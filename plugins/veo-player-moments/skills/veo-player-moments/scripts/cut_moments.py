#!/usr/bin/env python3
"""Cut a verified Veo player-moments manifest into separate MP4 files."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlparse


def fail(message: str) -> NoReturn:
    raise SystemExit(message)


def load_manifest(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Cannot read manifest {path}: {exc}")

    source = payload.get("source_video_url")
    parsed = urlparse(source if isinstance(source, str) else "")
    if parsed.scheme != "https" or parsed.hostname != "c.veocdn.com" or not parsed.path.endswith(".mp4"):
        fail("source_video_url must be an HTTPS c.veocdn.com .mp4 URL")

    moments = payload.get("moments")
    if not isinstance(moments, list) or not moments:
        fail("manifest moments must be a non-empty array")
    if payload.get("reported_moment_count") != len(moments):
        fail("reported_moment_count does not equal the moments array length")

    previous_start = -1.0
    source_duration = payload.get("source_duration_seconds")
    if source_duration is not None and (
        not isinstance(source_duration, (int, float))
        or not math.isfinite(source_duration)
        or source_duration <= 0
    ):
        fail("source_duration_seconds must be a positive finite number when present")
    for expected_index, moment in enumerate(moments, start=1):
        if not isinstance(moment, dict) or moment.get("index") != expected_index:
            fail(f"moment {expected_index} has a missing or non-consecutive index")
        start = moment.get("start_seconds")
        duration = moment.get("duration_seconds")
        if not isinstance(start, (int, float)) or not math.isfinite(start) or start < 0:
            fail(f"moment {expected_index} has an invalid start_seconds")
        if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
            fail(f"moment {expected_index} has an invalid duration_seconds")
        if start <= previous_start:
            fail(f"moment {expected_index} is not strictly later than the preceding moment")
        if source_duration is not None and start + duration > source_duration:
            fail(f"moment {expected_index} exceeds source_duration_seconds")
        previous_start = float(start)
    return payload


def duration_with_ffprobe(ffprobe: str, path: Path) -> float:
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return 0.0
    try:
        value = float(result.stdout.strip())
    except ValueError:
        return 0.0
    return value if math.isfinite(value) and value > 0 else 0.0


def clip_name(moment: dict) -> str:
    start_ms = round(float(moment["start_seconds"]) * 1000)
    duration_ms = round(float(moment["duration_seconds"]) * 1000)
    return f"moment-{moment['index']:03d}-start-{start_ms:010d}ms-duration-{duration_ms:06d}ms.mp4"


def command_for(ffmpeg: str, source: str, moment: dict, destination: Path, mode: str) -> list[str]:
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-ss",
        f"{float(moment['start_seconds']):.3f}",
        "-i",
        source,
        "-t",
        f"{float(moment['duration_seconds']):.3f}",
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
    ]
    if mode == "copy":
        command += ["-c", "copy", "-avoid_negative_ts", "make_zero"]
    else:
        command += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "128k"]
    return command + ["-movflags", "+faststart", "-y", str(destination)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--mode", choices=("copy", "precise"), default="copy")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    output_dir = args.output_dir.resolve()
    payload = load_manifest(manifest_path)

    ffmpeg = shutil.which(args.ffmpeg)
    ffprobe = shutil.which(args.ffprobe)
    if not args.dry_run and (not ffmpeg or not ffprobe):
        fail("FFmpeg and FFprobe are required on PATH (or pass --ffmpeg and --ffprobe)")
    ffmpeg = ffmpeg or args.ffmpeg
    ffprobe = ffprobe or args.ffprobe

    output_dir.mkdir(parents=True, exist_ok=True)
    destination_manifest = output_dir / "moments.json"
    if destination_manifest != manifest_path:
        if destination_manifest.exists() and destination_manifest.read_bytes() != manifest_path.read_bytes():
            fail(f"Refusing to replace a different manifest at {destination_manifest}")
        shutil.copy2(manifest_path, destination_manifest)

    report = {
        "manifest": str(destination_manifest),
        "source_video_url": payload["source_video_url"],
        "mode": args.mode,
        "expected": len(payload["moments"]),
        "created": 0,
        "skipped_verified": 0,
        "failed": [],
        "clips": [],
    }

    for moment in payload["moments"]:
        destination = output_dir / clip_name(moment)
        existing_duration = 0.0 if args.dry_run or not destination.exists() else duration_with_ffprobe(ffprobe, destination)
        if existing_duration > 0:
            status = "skipped_verified"
            report["skipped_verified"] += 1
            verified_duration = existing_duration
        elif destination.exists() and not args.dry_run:
            status = "failed_existing_invalid"
            verified_duration = 0.0
            report["failed"].append(moment["index"])
        elif args.dry_run:
            status = "dry_run"
            verified_duration = 0.0
        else:
            temporary = destination.with_suffix(".partial.mp4")
            if temporary.exists():
                temporary.unlink()
            result = subprocess.run(command_for(ffmpeg, payload["source_video_url"], moment, temporary, args.mode))
            verified_duration = duration_with_ffprobe(ffprobe, temporary) if result.returncode == 0 else 0.0
            if result.returncode != 0 or verified_duration <= 0:
                if temporary.exists():
                    temporary.unlink()
                status = "failed"
                report["failed"].append(moment["index"])
            else:
                temporary.replace(destination)
                status = "created"
                report["created"] += 1
        report["clips"].append(
            {
                "index": moment["index"],
                "file": destination.name,
                "status": status,
                "verified_duration_seconds": round(verified_duration, 3),
            }
        )
        print(f"[{moment['index']:03d}/{len(payload['moments']):03d}] {status}: {destination.name}", flush=True)

    report["verified"] = sum(1 for clip in report["clips"] if clip["verified_duration_seconds"] > 0)
    report["total_verified_duration_seconds"] = round(
        sum(clip["verified_duration_seconds"] for clip in report["clips"]), 3
    )
    report_path = output_dir / "download-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {report_path}")
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
