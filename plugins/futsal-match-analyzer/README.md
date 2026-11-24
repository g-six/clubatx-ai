# ClubAtx Futsal Match Recording Analysis

A local Codex plugin for visual analysis of MP4 futsal recordings. The assistant
reviews timestamped frame grids, checks candidate events at higher density, and
exports a timestamped event log, coverage notes and optional MP4 evidence clips.

The Python server handles video extraction and evidence bookkeeping. The host
assistant interprets the images. This is **agent-assisted sampled review**, not
a standalone automatic event detector or a guarantee of every event in a match.

## Requirements

- Codex or another plugin host supporting local stdio MCP servers and image tools.
- Python 3.9 or newer, plus installed `ffmpeg` and `ffprobe`. The server uses PATH first and
  falls back to standard system/Homebrew executable locations for desktop hosts.
- A readable absolute local `.mp4` path.

No Python packages, API key, ClubAtx login or hosted backend are required. The
server makes no network calls. When requested, the host assistant can separately
publish reviewed events using an authorized ClubAtx connection; this optional
step follows the bundled skill and is not performed by the local server. Sampled images are returned to the host assistant
for interpretation under that host's normal data handling.

```sh
python3 server/server.py --check
```

## Load locally

This directory is the plugin source. It includes portable `plugin.json` and
`mcp.json`, plus `.codex-plugin/plugin.json` and `.mcp.json` for Codex compatibility.
Use the host's local plugin installation flow and select this directory. A custom
Codex marketplace must be registered before its plugins can be installed. Merely
creating or unzipping this package does not install it.

For a host that accepts MCP configuration directly, configure the server with
`python3` as the command and the **absolute** path to `server/server.py` as the
only argument. Both plugin configurations use the host-expanded `${PLUGIN_ROOT}`
placeholder; it is not a shell variable that you need to export.

After loading, verify that these tools appear: `inspect_recording`,
`review_window`, `mark_reviewed`, `export_clip`, `export_report`.
Select the bundled `analyze-futsal-recording` skill when using a generic MCP host
that does not discover plugin skills automatically.

## Example request

> Analyze the futsal recording at `/absolute/path/to/match.mp4`. Blue is ClubAtx.
> Find goals, shots, saves, turnovers and restarts, and produce an event report.

The assistant inspects the file, screens the requested range, revisits candidate
events at 4fps or faster, and exports:

- `events.json`: events, source, evidence windows, sample targets and coverage gaps.
- `events.csv`: spreadsheet-friendly event log with video timestamps.
- `report.md`: readable match-event report and limitations.
- Optional `clip-*.mp4` files, with up to 120 seconds per clip.

Outputs use a new temporary directory per recording and new report/clip names;
the source recording is unchanged. Ask the assistant to copy deliverables to a
durable directory if needed. Recording IDs and review state are held in memory
for the current server process; exported reports persist until the OS cleans up
temporary files. Restarting requires inspecting and reviewing again.

## Optional ClubAtx fixture publishing

When asked to save reviewed events, the skill follows the [fixture publishing
workflow](skills/analyze-futsal-recording/references/clubatx-fixture-publishing.md):
verify the first kickoff as timeline 0:00, preserve exact video timestamps,
attach the source Veo MP4 to Match video, and start event Play links 2.2 seconds
before each event. It preserves the official score, records confirmed offensive
fouls/disallowed finishes, and leaves unmatched original events untimed.
Re-imports preserve existing IDs/admin links, revisit shooter jerseys, link only
uniquely supported players, and attach verified clips to existing scoresheet
goals without adding goals. Ambiguous identities remain explicitly unresolved.
The fixture experience includes admin attribution inside the video modal and
explicit event seeking; those require website support, not only this plugin.
An authorized service connection is needed for publishing, not local analysis.

## Center-spot review cue

The review workflow looks for ball placement at the center of the circle on the
halfway line, then follows the restart. Possible post-goal kickoffs prompt a
backward review of the preceding attack, including offensive fouls and pre-shot
stoppages. Period starts and retakes are distinguished; center placement alone
does not prove a goal. Kickoff timing uses the first touch that starts play.

## Analysis limits

Video timestamps are elapsed recording time. The futsal game clock is recorded
only when observed or explicitly synchronized. Unknown teams and players remain
unknown. Sparse frames can miss events; even 100% **sampled span** coverage does
not mean continuous playback coverage. Evidence checks enforce reviewed windows
and minimum density for confirmed events, but do not independently validate the
assistant's visual classification. Occlusions, camera cuts, unreadable numbers,
replays, and off-camera actions may prevent confirmation. Synthetic tests below
verify the media pipeline, not sports recognition quality.

## Development checks

```sh
python3 -m unittest discover -s tests -v
```

Tests create synthetic MP4s, exercise the stdio MCP handshake and tool discovery,
extract frame grids, check evidence validation and coverage, and export playable
clips and reports. They require FFmpeg. No match file is bundled.

The server implements the documented [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
and [tool results with image content](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).
