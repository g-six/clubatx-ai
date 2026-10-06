---
name: veo-player-clips
description: Create verified local MP4 clips for one soccer, basketball, or futsal player from an ordinary authenticated Veo match recording, identifying the player by team jersey color and jersey number. Use for player highlight, involvement, offense, defense, or full-shift clip requests from app.veo.co match URLs. Do not use when a Veo Player Moments URL already supplies the authoritative moment list.
---

# Veo Player Clips

Create an auditable set of clips for one player. Favor correct identity over clip count: omit ambiguous sequences and disclose them instead of clipping the wrong player.

## Inputs

Require:

- an exact HTTPS `app.veo.co` ordinary match URL;
- `sport`: `soccer`, `basketball`, or `futsal`;
- team name or side;
- jersey color;
- positive integer jersey number.

If `sport` is omitted, infer it only when the footage makes it unmistakable and state the inference. Otherwise ask for the sport before identifying actions or setting clip boundaries.

Accept optional parameters:

- `game_start`: Veo video-clock timestamp of live play;
- `scope`: `all-visible`, `ball-involvements`, `offense`, `defense`, `scoring`, or a natural-language subset; default `ball-involvements`;
- `pre_roll_seconds` and `post_roll_seconds`; default 4 and 3;
- `output`: `individual`, `compilation`, or `both`; default `both`;
- `mode`: `copy` for fast keyframe-aligned cuts or `precise` for re-encoded boundaries; default `precise`;
- `depth`: `light`, `medium`, or `high`; default `medium`;
- `output_dir`: local destination; otherwise create a clearly named folder in the current workspace or writable task-output directory.

Interpret scope and action boundaries for the selected sport:

- `soccer`: include enough buildup and aftermath to understand passes, carries, duels, recoveries, shots, chances, set pieces, and defensive actions. Use longer boundaries when the player's action creates a later outcome.
- `basketball`: organize clips by possessions and transitions; include the setup and outcome of drives, passes, screens, rebounds, shots, turnovers, and defensive sequences.
- `futsal`: expect rapid transitions and frequent substitutions. Use tighter possession boundaries, but preserve the preceding rotation or press that creates the action.

Natural-language scopes may use sport-specific concepts. Do not reinterpret a soccer shot as a basketball shot or merge distinct futsal transitions merely because they occur close together.

Depth controls search density, not identity standards:

- `light`: scan the full playable recording and capture unmistakable major involvements.
- `medium`: review the full recording at regular intervals, then inspect every candidate sequence at higher temporal density.
- `high`: densely review the full recording, including off-ball actions relevant to scope, substitutions, and short re-entry windows.

## Access and source video

1. Validate HTTPS and host `app.veo.co` exactly. Preserve the exact URL.
2. Use the Browser workflow with the user's existing authenticated session. Name the session and navigate directly to the supplied match.
3. If unauthenticated, keep the tab available and ask the user to sign in there. Never request or fill credentials.
4. Confirm the rendered match title and duration. Stop on access denial or a mismatched match.
5. Read the loaded video element's actual source or download it through the media element when supported. Accept only the standard match recording from `c.veocdn.com` or the resulting local MP4. Do not click Veo Share, Create clip, or edit controls.
6. Use FFprobe to verify that the source is a readable video and record its exact duration.

## Identify and verify the player

Review the full playable interval at the requested depth. Contact sheets may find candidates, but never use a single sparse frame as final identity proof. Reinspect each candidate as a short chronological sequence.

For every included interval:

- confirm that the court or field and play pattern agree with the selected `sport`;
- visually confirm the requested jersey color;
- confirm the requested jersey number within the sequence, or maintain continuous visual tracking from a nearby frame where the number is clear;
- ensure no same-color teammate substitution, crossing, camera cut, or occlusion breaks the identity chain;
- verify that the action matches `scope`;
- choose boundaries that preserve the action's setup and outcome, then apply pre/post-roll without exceeding source bounds.

When the jersey number is unreadable after an occlusion, end the interval before identity is lost. Resume only after independently reacquiring the number. Exclude candidates with unresolved identity and list their approximate timestamps as ambiguous.

Use confidence labels:

- `verified`: number is readable in the sequence and color/team agree;
- `tracked`: number is readable immediately before or after and identity remains continuously visible;
- never include `ambiguous` candidates.

Merge overlapping or immediately adjacent intervals that describe one continuous action. Keep separate possessions as separate clips unless the user requests longer shifts.

## Manifest and cutting

Create `player-clips.json` before cutting. Use this shape:

```json
{
  "source_page_url": "https://app.veo.co/matches/.../",
  "source_video": "/absolute/path/to/video.mp4",
  "source_duration_seconds": 3274.304,
  "match_title": "Rendered match title",
  "sport": "basketball",
  "player": {
    "team": "Elevate U14",
    "jersey_color": "black",
    "jersey_number": 8
  },
  "scope": "ball-involvements",
  "pre_roll_seconds": 4,
  "post_roll_seconds": 3,
  "clips": [
    {
      "index": 1,
      "start_seconds": 118.2,
      "end_seconds": 132.8,
      "label": "transition drive",
      "confidence": "verified",
      "verification_seconds": [120.1, 128.4]
    }
  ]
}
```

`source_video` may instead be the verified HTTPS `c.veocdn.com` standard MP4 URL. Clip indexes must be consecutive; intervals must be ordered, positive, non-overlapping, and within the source duration. `verification_seconds` must fall inside its interval.

Run the bundled cutter:

```bash
python3 scripts/cut_player_clips.py \
  --manifest /absolute/path/to/player-clips.json \
  --output-dir /absolute/path/to/output \
  --mode precise \
  --compilation
```

Omit `--compilation` for individual files only. Use `--mode copy` only when the user prefers speed and accepts keyframe-aligned starts. Never install FFmpeg without approval.

Do not overwrite a different manifest or a non-empty invalid clip. The helper resumes by skipping already verified outputs.

## Verification and delivery

Require successful FFmpeg completion and positive FFprobe duration for every individual clip and the requested compilation. Spot-check the first, middle, and final frames of each output for player identity and action continuity; for high depth, inspect more densely when occlusion occurs.

Deliver:

- the output directory;
- `player-clips.json`;
- `clip-report.json`;
- all verified individual clips and, when requested, `player-compilation.mp4`;
- included clip count and total duration;
- excluded ambiguous timestamps and the reason;
- the boundary mode and its precision caveat.

Keep the textual response concise; the media files are the primary output. Do not claim exhaustive coverage unless the complete playable interval was reviewed at the requested depth.
