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
from typing import NoReturn
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
        if clip.get("confidence") not in {"verified", "tracked"}:
            fail(f"clip {expected} confidence must be verified or tracked")
        verification = clip.get("verification_seconds")
        if not isinstance(verification, list) or not verification:
            fail(f"clip {expected} requires verification_seconds")
        if any(not valid_number(t) or t < start or t > end for t in verification):
            fail(f"clip {expected} has verification_seconds outside its interval")
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


def cut_command(ffmpeg: str, source: str, clip: dict, output: Path, mode: str) -> list[str]:
    duration = float(clip["end_seconds"]) - float(clip["start_seconds"])
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
        "-ss", f"{float(clip['start_seconds']):.3f}", "-i", source,
        "-t", f"{duration:.3f}", "-map", "0:v:0", "-map", "0:a?",
    ]
    if mode == "copy":
        command += ["-c", "copy", "-avoid_negative_ts", "make_zero"]
    else:
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
