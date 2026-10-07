#!/usr/bin/env python3
"""Cut a verified player-clip manifest into MP4s and an optional compilation."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn, Optional
from urllib.parse import urlparse


def fail(message: str) -> NoReturn:
    raise SystemExit(message)


def valid_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_source(value: object) -> str:
    if not isinstance(value, str) or not value:
        fail("source_video must be a non-empty string")
    parsed = urlparse(value)
    if parsed.scheme:
        if parsed.scheme != "https" or parsed.hostname != "c.veocdn.com" or not parsed.path.endswith(".mp4"):
            fail("remote source_video must be an HTTPS c.veocdn.com .mp4 URL")
        return value
    path = Path(value)
    if not path.is_absolute() or path.suffix.lower() != ".mp4" or not path.is_file():
        fail("local source_video must be an existing absolute .mp4 path")
    return str(path)


def load_manifest(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Cannot read manifest {path}: {exc}")

    payload["source_video"] = validate_source(payload.get("source_video"))
    duration = payload.get("source_duration_seconds")
    if not valid_number(duration) or duration <= 0:
        fail("source_duration_seconds must be positive")

    sport = payload.get("sport")
    if sport not in {"soccer", "basketball", "futsal"}:
        fail("sport must be soccer, basketball, or futsal")

    player = payload.get("player")
    if not isinstance(player, dict):
        fail("player must be an object")
    if not isinstance(player.get("team"), str) or not player["team"].strip():
        fail("player.team must be non-empty")
    if not isinstance(player.get("jersey_color"), str) or not player["jersey_color"].strip():
        fail("player.jersey_color must be non-empty")
    jersey_number = player.get("jersey_number")
    if not isinstance(jersey_number, int) or isinstance(jersey_number, bool) or jersey_number <= 0:
        fail("player.jersey_number must be a positive integer")

    clips = payload.get("clips")
    if not isinstance(clips, list) or not clips:
        fail("clips must be a non-empty array")
    prior_end = -1.0
    for expected, clip in enumerate(clips, 1):
        if not isinstance(clip, dict) or clip.get("index") != expected:
            fail(f"clip {expected} has a missing or non-consecutive index")
        start, end = clip.get("start_seconds"), clip.get("end_seconds")
        if not valid_number(start) or not valid_number(end) or start < 0 or end <= start:
            fail(f"clip {expected} has invalid boundaries")
        if start < prior_end:
            fail(f"clip {expected} overlaps the preceding clip")
        if end > duration:
            fail(f"clip {expected} exceeds source_duration_seconds")
        event_type = clip.get("event_type")
        if event_type not in {"regular", "goal", "basketball_score", "off_ball"}:
            fail(f"clip {expected} has an invalid event_type")
        if event_type == "goal" and sport not in {"soccer", "futsal"}:
            fail(f"clip {expected} goal is only valid for soccer or futsal")
        if event_type == "basketball_score" and sport != "basketball":
            fail(f"clip {expected} basketball_score requires basketball")

        if event_type in {"goal", "basketball_score"}:
            required_outcome = "goal" if event_type == "goal" else "made_basket"
            if clip.get("scoring_outcome") != required_outcome:
                fail(f"clip {expected} scoring_outcome must be {required_outcome}")
            outcome_times = clip.get("outcome_verification_seconds")
            execution = clip.get("execution_seconds")
            if not isinstance(outcome_times, list) or not outcome_times:
                fail(f"clip {expected} requires outcome_verification_seconds")
            if not valid_number(execution) or any(not valid_number(t) or t < execution or t > end for t in outcome_times):
                fail(f"clip {expected} has invalid outcome_verification_seconds")
            if event_type == "basketball_score":
                evidence = clip.get("outcome_evidence")
                if not isinstance(evidence, list) or not evidence:
                    fail(f"clip {expected} basketball_score requires outcome_evidence")
                allowed_observations = {
                    "rim_contact", "backboard_contact", "rim_roll", "ball_below_rim_after_net",
                    "opponent_collects_for_inbound",
                }
                for evidence_index, item in enumerate(evidence, 1):
                    if not isinstance(item, dict) or item.get("observation") not in allowed_observations:
                        fail(f"clip {expected} outcome evidence {evidence_index} has an invalid observation")
                    evidence_time = item.get("source_seconds")
                    if not valid_number(evidence_time) or evidence_time < execution or evidence_time > end:
                        fail(f"clip {expected} outcome evidence {evidence_index} has an invalid source_seconds")
                if not any(item["observation"] == "ball_below_rim_after_net" for item in evidence):
                    fail(f"clip {expected} basketball_score requires ball_below_rim_after_net evidence")
        elif any(key in clip for key in ("scoring_outcome", "outcome_verification_seconds", "outcome_evidence")):
            fail(f"clip {expected} has scoring evidence but is not a scoring event")

        if event_type == "regular":
            action_start, action_end, lead, tail = clip.get("receive_seconds"), clip.get("release_seconds"), 2.0, 1.0
        elif event_type in {"goal", "basketball_score"}:
            action_start = action_end = clip.get("execution_seconds")
            lead, tail = 2.0, 3.0 if event_type == "goal" else 2.0
        else:
            action_start, action_end, lead, tail = clip.get("action_start_seconds"), clip.get("action_end_seconds"), 2.0, 1.0
        if not valid_number(action_start) or not valid_number(action_end) or action_end < action_start:
            fail(f"clip {expected} has invalid action timestamps for {event_type}")
        expected_start = max(float(action_start) - lead, 0.0)
        default_end = float(action_end) + tail
        positive_outcome = clip.get("positive_outcome")
        if event_type in {"goal", "basketball_score"} and positive_outcome is None:
            fail(f"clip {expected} scoring events require positive_outcome")
        if positive_outcome is not None:
            if not isinstance(positive_outcome, dict):
                fail(f"clip {expected} positive_outcome must be an object")
            positive_type = positive_outcome.get("type")
            achieved = positive_outcome.get("achieved_seconds")
            positive_verification = positive_outcome.get("verification_seconds")
            if not isinstance(positive_type, str) or not positive_type.strip():
                fail(f"clip {expected} positive_outcome requires a concrete type")
            if not valid_number(achieved) or achieved < action_end or achieved > duration:
                fail(f"clip {expected} positive_outcome has invalid achieved_seconds")
            if not isinstance(positive_verification, list) or not positive_verification:
                fail(f"clip {expected} positive_outcome requires verification_seconds")
            if any(not valid_number(t) or t < action_end or t > duration for t in positive_verification):
                fail(f"clip {expected} positive_outcome has invalid verification_seconds")
            if not any(abs(float(t) - float(achieved)) <= 0.051 for t in positive_verification):
                fail(f"clip {expected} positive_outcome verification must include achieved_seconds")
            if event_type in {"goal", "basketball_score"}:
                if positive_type != clip.get("scoring_outcome"):
                    fail(f"clip {expected} positive_outcome type must match scoring_outcome")
                if not any(abs(float(t) - float(achieved)) <= 0.051
                           for t in clip["outcome_verification_seconds"]):
                    fail(f"clip {expected} scoring verification must match positive_outcome achieved_seconds")
                if event_type == "basketball_score" and not any(
                        item["observation"] == "ball_below_rim_after_net"
                        and abs(float(item["source_seconds"]) - float(achieved)) <= 0.051
                        for item in clip["outcome_evidence"]):
                    fail(f"clip {expected} made-basket achieved_seconds must match ball_below_rim_after_net evidence")
            default_end = max(default_end, float(achieved) + 1.5)
        expected_end = min(default_end, float(duration))
        if positive_outcome is not None and any(
                float(t) > expected_end for t in positive_outcome["verification_seconds"]):
            fail(f"clip {expected} positive_outcome verification falls outside its extended interval")
        if abs(float(start) - expected_start) > 0.051 or abs(float(end) - expected_end) > 0.051:
            fail(f"clip {expected} boundaries do not match the {event_type} timing policy")
        if clip.get("confidence") not in {"verified", "tracked"}:
            fail(f"clip {expected} confidence must be verified or tracked")
        verification = clip.get("verification_seconds")
        if not isinstance(verification, list) or not verification:
            fail(f"clip {expected} requires verification_seconds")
        if any(not valid_number(t) or t < start or t > end for t in verification):
            fail(f"clip {expected} has verification_seconds outside its interval")

        actions = clip.get("player_actions")
        if not isinstance(actions, list) or not actions:
            fail(f"clip {expected} requires player_actions")
        ball_actions = {
            "receive", "control", "pass", "carry", "dribble", "shot", "score", "goal", "turnover",
            "rebound", "loose_ball", "steal", "interception", "tackle", "save", "block", "deflection",
            "out_of_bounds_touch", "direct_contest",
        }
        off_ball_actions = {"screen", "cut", "closeout", "press", "mark", "recovery_run"}
        allowed_actions = ball_actions | off_ball_actions
        for action_index, action in enumerate(actions, 1):
            if not isinstance(action, dict) or action.get("type") not in allowed_actions:
                fail(f"clip {expected} player action {action_index} has an invalid type")
            action_time = action.get("source_seconds")
            identity_times = action.get("identity_verification_seconds")
            if not valid_number(action_time) or action_time < start or action_time > end:
                fail(f"clip {expected} player action {action_index} has an invalid source_seconds")
            if not isinstance(identity_times, list) or not identity_times:
                fail(f"clip {expected} player action {action_index} requires identity_verification_seconds")
            if any(not valid_number(t) or t < start or t > end or abs(t - action_time) > 2.0 for t in identity_times):
                fail(f"clip {expected} player action {action_index} has invalid identity evidence")
        if payload.get("scope") == "ball-involvements" and any(action["type"] not in ball_actions for action in actions):
            fail(f"clip {expected} contains off-ball actions outside ball-involvements scope")
        action_types = {action["type"] for action in actions}
        if event_type == "basketball_score" and "score" not in action_types:
            fail(f"clip {expected} basketball_score requires a score player action")
        if event_type == "goal" and "goal" not in action_types:
            fail(f"clip {expected} goal requires a goal player action")

        framing = clip.get("framing", {"zoom": 1.0})
        if not isinstance(framing, dict) or framing.get("zoom") not in {1, 1.0, 1.5}:
            fail(f"clip {expected} framing.zoom must be 1.0 or 1.5")
        points = framing.get("track_points", [])
        if framing.get("zoom") == 1.5:
            if not isinstance(points, list) or not points:
                fail(f"clip {expected} zoom 1.5 requires track_points")
            previous_point_time = -1.0
            for point in points:
                if not isinstance(point, dict):
                    fail(f"clip {expected} has an invalid track point")
                point_time, x, y = point.get("source_seconds"), point.get("x"), point.get("y")
                if (not valid_number(point_time) or point_time < start or point_time > end
                        or not valid_number(x) or not 0 <= x <= 1
                        or not valid_number(y) or not 0 <= y <= 1
                        or point_time <= previous_point_time):
                    fail(f"clip {expected} has invalid or unordered track_points")
                previous_point_time = float(point_time)
        elif points:
            fail(f"clip {expected} track_points require zoom 1.5")
        prior_end = float(end)
    return payload


def duration_with_ffprobe(ffprobe: str, path: Path) -> float:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        text=True,
    )
    try:
        value = float(result.stdout.strip()) if result.returncode == 0 else 0.0
    except ValueError:
        return 0.0
    return value if math.isfinite(value) and value > 0 else 0.0


def slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return text[:48] or "clip"


def clip_name(clip: dict) -> str:
    return f"clip-{clip['index']:03d}-{slug(clip.get('label', 'play'))}.mp4"


def interpolation_expression(points: list[dict], axis: str, clip_start: float) -> str:
    values = [(float(point["source_seconds"]) - clip_start, float(point[axis])) for point in points]
    if len(values) == 1:
        return f"{values[0][1]:.8f}"
    expression = f"{values[-1][1]:.8f}"
    for index in range(len(values) - 2, -1, -1):
        t0, v0 = values[index]
        t1, v1 = values[index + 1]
        slope = (v1 - v0) / (t1 - t0)
        segment = f"({v0:.8f}+({slope:.10f})*(t-{t0:.6f}))"
        expression = f"if(lt(t,{t0:.6f}),{v0:.8f},if(lt(t,{t1:.6f}),{segment},{expression}))"
    return expression


def framing_filter(clip: dict) -> Optional[str]:
    framing = clip.get("framing", {"zoom": 1.0})
    if float(framing.get("zoom", 1.0)) == 1.0:
        return None
    zoom = 1.5
    clip_start = float(clip["start_seconds"])
    x_center = interpolation_expression(framing["track_points"], "x", clip_start)
    y_center = interpolation_expression(framing["track_points"], "y", clip_start)
    crop_w = f"trunc(iw/{zoom}/2)*2"
    crop_h = f"trunc(ih/{zoom}/2)*2"
    crop_x = f"max(0,min(iw-ow,({x_center})*iw-ow/2))"
    crop_y = f"max(0,min(ih-oh,({y_center})*ih-oh/2))"
    return (
        "setpts=PTS-STARTPTS,"
        f"crop=w='{crop_w}':h='{crop_h}':x='{crop_x}':y='{crop_y}',"
        f"scale=w='trunc(iw*{zoom}/2)*2':h='trunc(ih*{zoom}/2)*2'"
    )


def cut_command(ffmpeg: str, source: str, clip: dict, output: Path, mode: str) -> list[str]:
    duration = float(clip["end_seconds"]) - float(clip["start_seconds"])
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
        "-ss", f"{float(clip['start_seconds']):.3f}", "-i", source,
        "-t", f"{duration:.3f}", "-map", "0:v:0", "-map", "0:a?",
    ]
    video_filter = framing_filter(clip)
    if mode == "copy":
        command += ["-c", "copy", "-avoid_negative_ts", "make_zero"]
    else:
        if video_filter:
            command += ["-vf", video_filter]
        command += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "128k"]
    return command + ["-movflags", "+faststart", "-y", str(output)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--mode", choices=("copy", "precise"), default="precise")
    parser.add_argument("--compilation", action="store_true")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = load_manifest(args.manifest.resolve())
    if args.mode == "copy" and any(framing_filter(clip) for clip in payload["clips"]):
        fail("Zoomed clips require --mode precise")
    output_dir = args.output_dir.resolve()
    ffmpeg = shutil.which(args.ffmpeg)
    ffprobe = shutil.which(args.ffprobe)
    if not args.dry_run and (not ffmpeg or not ffprobe):
        fail("FFmpeg and FFprobe are required on PATH")
    ffmpeg, ffprobe = ffmpeg or args.ffmpeg, ffprobe or args.ffprobe
    output_dir.mkdir(parents=True, exist_ok=True)

    destination_manifest = output_dir / "player-clips.json"
    source_manifest = args.manifest.resolve()
    if destination_manifest != source_manifest:
        if destination_manifest.exists() and destination_manifest.read_bytes() != source_manifest.read_bytes():
            fail(f"Refusing to replace a different manifest at {destination_manifest}")
        shutil.copy2(source_manifest, destination_manifest)

    report = {
        "manifest": str(destination_manifest), "source_video": payload["source_video"], "sport": payload["sport"],
        "mode": args.mode, "expected": len(payload["clips"]), "created": 0,
        "skipped_verified": 0, "failed": [], "clips": [], "compilation": None,
    }
    verified_paths: list[Path] = []
    for clip in payload["clips"]:
        destination = output_dir / clip_name(clip)
        existing = 0.0 if args.dry_run or not destination.exists() else duration_with_ffprobe(ffprobe, destination)
        if existing > 0:
            status, verified = "skipped_verified", existing
            report["skipped_verified"] += 1
        elif destination.exists() and not args.dry_run:
            status, verified = "failed_existing_invalid", 0.0
            report["failed"].append(clip["index"])
        elif args.dry_run:
            status, verified = "dry_run", 0.0
        else:
            temporary = destination.with_suffix(".partial.mp4")
            temporary.unlink(missing_ok=True)
            result = subprocess.run(cut_command(ffmpeg, payload["source_video"], clip, temporary, args.mode))
            verified = duration_with_ffprobe(ffprobe, temporary) if result.returncode == 0 else 0.0
            if verified <= 0:
                temporary.unlink(missing_ok=True)
                status = "failed"
                report["failed"].append(clip["index"])
            else:
                temporary.replace(destination)
                status = "created"
                report["created"] += 1
        if verified > 0:
            verified_paths.append(destination)
        report["clips"].append({"index": clip["index"], "file": destination.name, "status": status,
                                "event_type": clip["event_type"],
                                "semantic_outcome": clip.get("scoring_outcome"),
                                "positive_outcome": clip.get("positive_outcome"),
                                "outcome_evidence": clip.get("outcome_evidence"),
                                "player_actions": clip["player_actions"],
                                "zoom": float(clip.get("framing", {}).get("zoom", 1.0)),
                                "verified_duration_seconds": round(verified, 3)})
        print(f"[{clip['index']:03d}/{len(payload['clips']):03d}] {status}: {destination.name}", flush=True)

    if args.compilation and not args.dry_run and not report["failed"] and len(verified_paths) == len(payload["clips"]):
        compilation = output_dir / "player-compilation.mp4"
        existing = duration_with_ffprobe(ffprobe, compilation) if compilation.exists() else 0.0
        if existing <= 0 and compilation.exists():
            fail(f"Refusing to replace invalid existing compilation at {compilation}")
        if existing <= 0:
            concat_file = output_dir / ".player-clips-concat.txt"
            concat_file.write_text("".join(f"file '{path.name.replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n" for path in verified_paths), encoding="utf-8")
            temporary = compilation.with_suffix(".partial.mp4")
            temporary.unlink(missing_ok=True)
            result = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-f", "concat", "-safe", "0",
                                     "-i", str(concat_file), "-c", "copy", "-movflags", "+faststart", "-y", str(temporary)])
            concat_file.unlink(missing_ok=True)
            existing = duration_with_ffprobe(ffprobe, temporary) if result.returncode == 0 else 0.0
            if existing <= 0:
                temporary.unlink(missing_ok=True)
                fail("Compilation failed verification")
            temporary.replace(compilation)
        report["compilation"] = {"file": compilation.name, "verified_duration_seconds": round(existing, 3)}

    report["verified"] = sum(c["verified_duration_seconds"] > 0 for c in report["clips"])
    report["total_verified_duration_seconds"] = round(sum(c["verified_duration_seconds"] for c in report["clips"]), 3)
    report_path = output_dir / "clip-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {report_path}")
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
