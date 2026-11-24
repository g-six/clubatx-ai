#!/usr/bin/env python3
"""Local, dependency-free MCP tools for agent-assisted futsal video review.

Python 3.9+, ffmpeg and ffprobe required. No network or model API calls.
"""
import base64
import csv
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

VERSION = "0.1.6"
EVENT_TYPES = ["goal", "shot", "save", "block", "turnover", "counterattack",
               "kick_in", "corner", "goal_clearance", "free_kick", "penalty",
               "foul", "yellow_card", "red_card", "substitution", "timeout",
               "period_start", "period_end", "other"]


def text_result(data):
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]}


def number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return value


def nonblank(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonblank string")
    return value.strip()


MEDIA_BIN_DIRS = (Path('/opt/homebrew/bin'), Path('/usr/local/bin'), Path('/usr/bin'), Path('/bin'))


def media_executable(name):
    """Desktop hosts can have a narrower PATH than the user's login shell."""
    found = shutil.which(name)
    if found:
        return found
    for directory in MEDIA_BIN_DIRS:
        candidate = directory / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def run(command, timeout=45):
    command = list(command)
    if command[0] in ('ffmpeg', 'ffprobe'):
        resolved = media_executable(command[0])
        if resolved is None:
            raise ValueError(f"Missing executable {command[0]}; install FFmpeg and ensure it is on PATH")
        command[0] = resolved
    try:
        return subprocess.run(command, check=True, capture_output=True, timeout=timeout).stdout
    except FileNotFoundError as exc:
        raise ValueError(f"Missing executable {command[0]}; install FFmpeg and ensure it is on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Media operation timed out; try a smaller window") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError(exc.stderr.decode(errors="replace")[-1800:]) from exc


def timestamp(seconds):
    hours, rest = divmod(seconds, 3600)
    minutes, rest = divmod(rest, 60)
    return f"{int(hours):02}:{int(minutes):02}:{rest:06.3f}"


def merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1] + 0.001:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return merged


class Analyzer:
    def __init__(self):
        self.recordings = {}
        self.windows = {}

    def recording(self, recording_id):
        if recording_id not in self.recordings:
            raise ValueError("Unknown recording_id; inspect the file in this server session first")
        rec = self.recordings[recording_id]
        stat = rec["path"].stat()
        if (stat.st_size, stat.st_mtime_ns) != rec["fingerprint"]:
            raise ValueError("Recording changed; inspect it again before continuing")
        return rec

    def inspect_recording(self, path):
        path = Path(nonblank(path, "path")).expanduser()
        if not path.is_absolute():
            raise ValueError("Provide an absolute local MP4 path")
        path = path.resolve(strict=True)
        if not path.is_file() or path.suffix.lower() != ".mp4":
            raise ValueError("Expected a regular .mp4 file")
        data = json.loads(run(["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe",
                               "-show_format", "-show_streams", "-of", "json", str(path)]))
        video = next((s for s in data["streams"] if s["codec_type"] == "video"
                      and not s.get("disposition", {}).get("attached_pic")), None)
        if video is None:
            raise ValueError("MP4 contains no video stream")
        duration = float(video.get("duration") or data["format"].get("duration", 0))
        number(duration, "video duration", 0.001, 7 * 86400)
        rid = uuid.uuid4().hex[:12]
        root = Path(tempfile.mkdtemp(prefix=f"futsal-{rid}-"))
        stat = path.stat()
        rec = {"path": path, "fingerprint": (stat.st_size, stat.st_mtime_ns),
               "duration": duration, "root": root, "stream": video["index"]}
        self.recordings[rid] = rec
        return text_result({"recording_id": rid, "path": str(path), "duration_seconds": duration,
                            "width": video["width"], "height": video["height"],
                            "frame_rate": video.get("avg_frame_rate"), "output_directory": str(root),
                            "analysis": "No events detected yet. The agent must visually review sampled images.",
                            "timebase": "Elapsed video time from the first video frame; not the futsal game clock."})

    def review_window(self, recording_id, start_seconds, interval_seconds=1, count=24, width=480):
        rec = self.recording(recording_id)
        start = number(start_seconds, "start_seconds", 0, rec["duration"] - 0.001)
        interval = number(interval_seconds, "interval_seconds", 0.1, 10)
        number(count, "count", 1, 24)
        number(width, "width", 240, 1280)
        if int(count) != count or int(width) != width or int(width) % 2:
            raise ValueError("count must be an integer; width must be an even integer")
        count, width = int(count), int(width)
        times = [round(start + i * interval, 6) for i in range(count)
                 if start + i * interval < rec["duration"] - 0.001]
        wid = uuid.uuid4().hex[:12]
        folder = rec["root"] / wid
        folder.mkdir()
        height = width * 9 // 16
        height += height % 2
        scale = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                 f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1")
        # Separate accurate seeks avoid a sampling filter's timestamp rounding and drift.
        for index, position in enumerate(times):
            target = folder / f"frame-{index:03}.png"
            run(["ffmpeg", "-nostdin", "-v", "error", "-protocol_whitelist", "file,pipe",
                 "-ss", str(position), "-i", str(rec["path"]), "-map", f"0:{rec['stream']}",
                 "-vf", scale, "-frames:v", "1", "-update", "1", str(target)])
            if not target.exists() or target.stat().st_size == 0:
                raise ValueError(f"No decodable frame at {position}; no review window was registered")
        columns = min(4, len(times))
        rows = math.ceil(len(times) / columns)
        sheet = folder / "sheet.png"
        run(["ffmpeg", "-nostdin", "-v", "error", "-framerate", "1", "-i",
             str(folder / "frame-%03d.png"), "-vf", f"tile={columns}x{rows}:padding=2:margin=2",
             "-frames:v", "1", "-update", "1", str(sheet)])
        end = min(rec["duration"], times[-1] + interval)
        self.windows[wid] = {"recording_id": recording_id, "start": start, "end": end,
                             "times": times, "interval": interval, "reviewed": False,
                             "sheet": str(sheet)}
        result = text_result({"window_id": wid, "sampled_span_seconds": [start, end],
                              "interval_seconds": interval, "sheet_path": str(sheet),
                              "grid": {"columns": columns, "rows": rows, "order": "left to right, then top to bottom"},
                              "frames": [{"cell": i + 1, "seconds": t, "video_time": timestamp(t),
                                          "path": str(folder / f"frame-{i:03}.png")}
                                         for i, t in enumerate(times)],
                              "notice": "Seek targets approximate frame times within source frame precision. Blank trailing cells are not footage. Inspect images before calling mark_reviewed. Sampling can miss events between frames."})
        result["content"].append({"type": "image", "mimeType": "image/png",
                                  "data": base64.b64encode(sheet.read_bytes()).decode()})
        return result

    def mark_reviewed(self, window_id, notes):
        if window_id not in self.windows:
            raise ValueError("Unknown window_id")
        window = self.windows[window_id]
        self.recording(window["recording_id"])
        window.update(reviewed=True, notes=nonblank(notes, "notes"))
        return text_result({"window_id": window_id, "reviewed": True,
                            "notice": "Records the agent's review attestation, not independent verification."})

    def export_clip(self, recording_id, start_seconds, end_seconds):
        rec = self.recording(recording_id)
        start = number(start_seconds, "start_seconds", 0, rec["duration"])
        end = number(end_seconds, "end_seconds", start + 0.001, min(start + 120, rec["duration"]))
        target = rec["root"] / f"clip-{uuid.uuid4().hex[:12]}.mp4"
        run(["ffmpeg", "-nostdin", "-v", "error", "-protocol_whitelist", "file,pipe",
             "-ss", str(start), "-i", str(rec["path"]), "-t", str(end - start),
             "-map", f"0:{rec['stream']}", "-map", "0:a:0?", "-c:v", "libx264",
             "-preset", "fast", "-crf", "20", "-c:a", "aac", "-movflags", "+faststart", str(target)], timeout=180)
        return text_result({"path": str(target), "start_seconds": start, "end_seconds": end,
                            "notice": "Clip exported; extraction does not count as visual review."})

    def export_report(self, recording_id, events, summary, team_labels=None):
        rec = self.recording(recording_id)
        nonblank(summary, "summary")
        if not isinstance(events, list) or len(events) > 10000:
            raise ValueError("events must be a list of at most 10000 observations")
        if team_labels is None:
            team_labels = []
        if not isinstance(team_labels, list) or any(not isinstance(t, str) for t in team_labels):
            raise ValueError("team_labels must be a list of strings")
        reviewed = {wid: w for wid, w in self.windows.items()
                    if w["recording_id"] == recording_id and w["reviewed"]}
        checked = []
        for event in events:
            if not isinstance(event, dict):
                raise ValueError("Each event must be an object")
            at = number(event.get("timestamp_seconds"), "timestamp_seconds", 0, rec["duration"])
            if event.get("type") not in EVENT_TYPES:
                raise ValueError(f"Unknown event type; choose from {EVENT_TYPES}")
            if event.get("status") not in ["confirmed", "candidate", "uncertain"]:
                raise ValueError("status must be confirmed, candidate or uncertain")
            nonblank(event.get("description"), "event description")
            evidence = event.get("evidence_window_ids")
            if not isinstance(evidence, list) or not evidence or any(not isinstance(w, str) or w not in reviewed for w in evidence):
                raise ValueError("Each event needs evidence_window_ids from reviewed windows of this recording")
            containing = [reviewed[w] for w in evidence if reviewed[w]["start"] <= at <= reviewed[w]["times"][-1]]
            if not containing:
                raise ValueError("Event timestamp must fall between actual evidence samples")
            if event["status"] == "confirmed" and not any(w["interval"] <= 0.25 and len(w["times"]) >= 2 for w in containing):
                raise ValueError("Confirmed events require reviewed evidence sampled at 4fps or faster")
            for key in ["team", "player", "match_clock"]:
                if event.get(key) is not None and not isinstance(event[key], str):
                    raise ValueError(f"{key} must be a string or null")
            checked.append({k: event.get(k) for k in ["timestamp_seconds", "type", "status", "team", "player", "match_clock", "description", "evidence_window_ids"]})
        checked.sort(key=lambda e: e["timestamp_seconds"])
        spans = merge_intervals([(w["start"], w["end"]) for w in reviewed.values()])
        gaps, cursor = [], 0
        for start, end in spans:
            if start > cursor:
                gaps.append([cursor, start])
            cursor = end
        if cursor < rec["duration"]:
            gaps.append([cursor, rec["duration"]])
        report = {"schema_version": 1, "recording": str(rec["path"]), "duration_seconds": rec["duration"],
                  "team_labels": team_labels, "summary": summary, "events": checked,
                  "coverage": {"sampled_review_spans": spans, "unreviewed_spans": gaps,
                               "sampled_span_percent": round(sum(b-a for a, b in spans) / rec["duration"] * 100, 2),
                               "unique_frame_targets_reviewed": len({t for w in reviewed.values() for t in w["times"]}),
                               "method": "Agent-attested visual review of sampled frames. Span coverage is not continuous-video coverage."},
                  "review_windows": reviewed,
                  "limitations": ["Sampling can miss fast actions between frames, even when sampled spans cover the whole file.",
                                  "Confirmed means agent-verified visual evidence, not automated referee or tracking ground truth.",
                                  "Video elapsed time differs from the stopped futsal game clock; match_clock is populated only from observed evidence.",
                                  "Counts summarize this event log only, not independently verified match totals."]}
        folder = rec["root"] / f"report-{uuid.uuid4().hex[:12]}"
        folder.mkdir()
        (folder / "events.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        buffer = io.StringIO()
        fields = ["timestamp_seconds", "video_time", "type", "status", "team", "player", "match_clock", "description", "evidence_window_ids"]
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader()
        for event in checked:
            row = dict(event, video_time=timestamp(event["timestamp_seconds"]), evidence_window_ids=",".join(event["evidence_window_ids"]))
            # Prevent spreadsheet formula execution when opening a CSV report.
            writer.writerow({k: ("'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v) for k, v in row.items()})
        (folder / "events.csv").write_text(buffer.getvalue())
        def cell(value):
            return str(value or "Unknown").replace("|", "\\|").replace("\n", " ").replace("\r", " ")
        lines = ["# ClubAtx Futsal Match Recording Analysis", "", summary, "",
                 f"Sampled span coverage: {report['coverage']['sampled_span_percent']}% (not continuous playback).", "",
                 "| Video time | Event | Status | Team | Player | Observation |", "|---|---|---|---|---|---|"]
        for event in checked:
            lines.append("| " + " | ".join([timestamp(event["timestamp_seconds"]), event["type"], event["status"], cell(event["team"]), cell(event["player"]), cell(event["description"])]) + " |")
        lines += ["", "## Limitations", ""] + ["- " + item for item in report["limitations"]]
        (folder / "report.md").write_text("\n".join(lines) + "\n")
        return text_result({"paths": {name: str(folder / name) for name in ["events.json", "events.csv", "report.md"]},
                            "coverage": report["coverage"], "event_count": len(checked)})


def schema(properties, required):
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


STRING = {"type": "string", "minLength": 1}
RID = {"recording_id": STRING}
EVENT_SCHEMA = schema({"timestamp_seconds": {"type": "number", "minimum": 0},
                       "type": {"enum": EVENT_TYPES}, "status": {"enum": ["confirmed", "candidate", "uncertain"]},
                       "team": {"type": ["string", "null"]}, "player": {"type": ["string", "null"]},
                       "match_clock": {"type": ["string", "null"]}, "description": STRING,
                       "evidence_window_ids": {"type": "array", "items": STRING, "minItems": 1}},
                      ["timestamp_seconds", "type", "status", "description", "evidence_window_ids"])
TOOLS = [
    ("inspect_recording", "Validate a local MP4 and return metadata and a recording_id. Does not detect events.", schema({"path": STRING}, ["path"]), True),
    ("review_window", "Extract chronological frames and return an image grid with per-cell video timestamps. Agent must inspect images; this is not event detection.", schema(dict(RID, start_seconds={"type": "number", "minimum": 0}, interval_seconds={"type": "number", "minimum": 0.1, "maximum": 10, "default": 1}, count={"type": "integer", "minimum": 1, "maximum": 24, "default": 24}, width={"type": "integer", "minimum": 240, "maximum": 1280, "default": 480}), ["recording_id", "start_seconds"]), False),
    ("mark_reviewed", "Attest that the agent visually inspected a returned window. Include observations, visibility, and candidate event times.", schema({"window_id": STRING, "notes": STRING}, ["window_id", "notes"]), False),
    ("export_clip", "Export up to 120 seconds as a new MP4 in the recording's output directory; source is never changed.", schema(dict(RID, start_seconds={"type": "number", "minimum": 0}, end_seconds={"type": "number", "minimum": 0}), ["recording_id", "start_seconds", "end_seconds"]), False),
    ("export_report", "Validate evidence-linked events and export JSON, CSV, Markdown and sampled-review coverage. Confirmed events need reviewed evidence at 4fps or faster.", schema(dict(RID, events={"type": "array", "items": EVENT_SCHEMA}, summary=STRING, team_labels={"type": "array", "items": STRING}), ["recording_id", "events", "summary"]), False),
]


def serve():
    analyzer = Analyzer()
    initialized = False
    ready = False
    for line in sys.stdin:
        request = None
        try:
            request = json.loads(line)
            if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
                raise ValueError("Invalid JSON-RPC request")
            method = request["method"]
            if "id" not in request:
                if method == "notifications/initialized" and initialized:
                    ready = True
                continue
            params = request.get("params", {})
            if not isinstance(params, dict):
                raise ValueError("params must be an object")
            if method == "initialize":
                requested = params.get("protocolVersion")
                version = requested if requested in ["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"] else "2025-11-25"
                result = {"protocolVersion": version, "capabilities": {"tools": {}},
                          "serverInfo": {"name": "futsal-match-analyzer", "version": VERSION},
                          "instructions": "Review frames visually before marking reviewed. Use the analyze-futsal-recording skill. Never infer a complete event log from sparse frames."}
                initialized = True
            elif method == "ping":
                result = {}
            elif not ready:
                raise ValueError("Initialize and send notifications/initialized first")
            elif method == "tools/list":
                result = {"tools": [{"name": name, "description": description, "inputSchema": spec,
                                     "annotations": {"readOnlyHint": read_only, "destructiveHint": False, "openWorldHint": False}}
                                    for name, description, spec, read_only in TOOLS]}
            elif method == "tools/call":
                name = params.get("name")
                if name not in [t[0] for t in TOOLS]:
                    raise ValueError("Unknown tool")
                arguments = params.get("arguments", {})
                if not isinstance(arguments, dict):
                    raise ValueError("arguments must be an object")
                spec = next(t[2] for t in TOOLS if t[0] == name)
                try:
                    if set(arguments) - set(spec["properties"]) or set(spec["required"]) - set(arguments):
                        raise ValueError("Missing required or unknown tool arguments")
                    result = getattr(analyzer, name)(**arguments)
                except (ValueError, OSError, TypeError, KeyError) as exc:
                    result = {"isError": True, "content": [{"type": "text", "text": str(exc)}]}
            else:
                response = {"jsonrpc": "2.0", "id": request["id"], "error": {"code": -32601, "message": "Method not found"}}
                print(json.dumps(response), flush=True)
                continue
            response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
        except json.JSONDecodeError:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        except (ValueError, TypeError) as exc:
            response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None,
                        "error": {"code": -32602, "message": str(exc)}}
        print(json.dumps(response, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == "__main__":
    if "--check" in sys.argv:
        missing = [name for name in ["ffmpeg", "ffprobe"] if media_executable(name) is None]
        print(json.dumps({"python": sys.version.split()[0], "missing_executables": missing}))
        sys.exit(bool(missing))
    serve()
