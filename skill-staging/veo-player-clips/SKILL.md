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
- `output`: `individual`, `compilation`, or `both`; default `both`;
- `mode`: `copy` for fast keyframe-aligned cuts or `precise` for re-encoded boundaries; default `precise`;
- `depth`: `light`, `medium`, or `high`; default `medium`;
- `output_dir`: local destination; otherwise create a clearly named folder in the current workspace or writable task-output directory.

Interpret scope and action boundaries for the selected sport:

- `soccer`: include enough buildup and aftermath to understand passes, carries, duels, recoveries, shots, chances, set pieces, and defensive actions. Use longer boundaries when the player's action creates a later outcome.
- `basketball`: organize clips by possessions and transitions; include the setup and outcome of drives, passes, screens, rebounds, shots, turnovers, and defensive sequences.
- `futsal`: expect rapid transitions and frequent substitutions. Use tighter possession boundaries, but preserve the preceding rotation or press that creates the action.

Natural-language scopes may use sport-specific concepts. Do not reinterpret a soccer shot as a basketball shot or merge distinct futsal transitions merely because they occur close together.

## Clip timing

Use these default boundaries unless the user explicitly requests different timing:

- `regular`: start exactly 2 seconds before the player receives or gains control of the ball; end exactly 1 second after the player passes, shoots, loses, or otherwise releases the ball.
- `goal` for soccer or futsal: start exactly 2 seconds before the scoring execution or final strike; end exactly 3 seconds after that execution so the outcome and initial celebration/reset are visible.
- `basketball_score`: start exactly 2 seconds before the shot release; end exactly 2 seconds after release. This is intentionally shorter than the soccer/futsal goal window.
- `off_ball`: only when requested by scope; start 2 seconds before the verified action begins and end 1 second after it ends.

When the same continuous sequence leads to a verified positive outcome, extend the clip end through the moment the outcome is achieved plus 1.5 seconds. Never shorten the normal sport-specific window: use the later of the default end or `positive_outcome.achieved_seconds + 1.5`. A positive outcome must be a concrete visible result directly produced by or flowing from the player's action, such as a made basket or goal, a teammate converting the player's pass, or a defensive action immediately yielding controlled possession. A promising attack, unconverted chance, unrelated later score, whistle, reaction, or inferred result does not qualify. Inspect through the terminal result before deciding whether the extension applies.

Clamp boundaries to the recording start/end. Record the underlying receive, release, execution, action, and positive-outcome timestamps in the manifest; do not merely approximate a start and end. If consecutive touch windows overlap, merge them into one continuous clip and preserve all underlying event timestamps.

## Scoring outcome verification

Keep technical media verification separate from semantic event verification. FFmpeg success, readable duration, or a correctly timed clip proves only that the MP4 is valid; it does not prove that a goal or basket occurred.

Before using `goal` or `basketball_score`:

- inspect the action continuously from execution through the outcome;
- for basketball, visibly confirm the ball passes through the hoop. A release, apparent shot, rim/backboard contact, air ball, blocked shot, rebound, whistle, or ball going out of bounds is not by itself a made basket;
- for soccer or futsal, visibly confirm the whole ball crosses the goal line between the posts and under the crossbar, or corroborate an obscured crossing with an unmistakable official goal signal and scoring restart;
- record the timestamp where the scoring outcome becomes visible as `outcome_verification_seconds` and as `positive_outcome.achieved_seconds`;
- set `scoring_outcome` to `made_basket` for basketball or `goal` for soccer/futsal.

If the outcome cannot be confirmed, classify the action accurately as a regular attempt, miss, block, save, rebound, turnover, or out-of-bounds sequence. Never infer a score from trajectory, player reaction, clip timing, filename, or a synthetic test manifest.

For every basketball shot, resolve the complete rim sequence before labeling it:

1. Decode a continuous close view of the hoop from shot release until the ball reaches a terminal outcome. When the ball contacts the rim or backboard, rolls around the rim, changes direction, or is briefly hidden by the rim/net, treat that as an intermediate state and continue frame by frame. Never label a miss at the first rim or backboard contact.
2. Use sufficiently dense frames to preserve every bounce; use the source frame rate or at least 30 fps around rim contact when lower-density sheets do not show the path unambiguously. Keep the frames in chronological order.
3. Confirm a make only when the ball can be followed into the cylinder and then below the rim through the net. Confirm a miss only when the ball clearly leaves the cylinder area without passing through and is then rebounded, goes out, or otherwise continues away from the hoop.
4. Inspect the wider view through the immediate restart as corroboration. An opponent collecting the ball under the basket may be an inbound after a make or a rebound after a miss, so possession alone is not decisive; the ball path through or away from the net controls the label.
5. If the terminal outcome occurs after the default output boundary, inspect beyond that boundary for classification and extend a positive-result clip through the achieved outcome plus 1.5 seconds. If the path still cannot be resolved, use an outcome-neutral regular-shot label rather than `basketball_score` or `miss`.

For a verified `basketball_score`, record `outcome_evidence` in the manifest with at least one timestamped `ball_below_rim_after_net` observation. Add intermediate observations such as `rim_contact`, `backboard_contact`, or `rim_roll` when present so a multi-bounce make remains auditable.

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

For `basketball` ball-involvement clips, add a second pass over high-value possessions before finalizing:

- inspect every visible possession where the player is on court and near the ball handler, a pass lane, a rebound, a shot, a turnover, or a transition advantage;
- include drives, catches, passes, rebounds, loose balls, defensive contests, and possessions that create a scoring chance even when they are brief;
- do not rely on 10-second or similarly sparse sheets to reject a possession where the player is near the ball. Generate a denser sheet or short sequence around the candidate before excluding it;
- when multiple same-color teammates are nearby, reacquire the jersey number after the play develops instead of dropping the candidate solely because the first frame is unclear.

When the user supplies a specific timestamp, mark, or suspected missed play, treat it as a priority candidate. Review at least 20 seconds before and after that timestamp at higher temporal density, verify the player's identity and action chain, then either add it to a revised manifest or explain the exact exclusion reason.

For every included interval:

- confirm that the court or field and play pattern agree with the selected `sport`;
- visually confirm the requested jersey color;
- confirm the requested jersey number within the sequence, or maintain continuous visual tracking from a nearby frame where the number is clear;
- ensure no same-color teammate substitution, crossing, camera cut, or occlusion breaks the identity chain;
- verify that the action matches `scope`;
- verify a concrete action by the requested player at the action timestamp, not merely the player's presence elsewhere in the frame;
- identify the receive/release, scoring execution, or off-ball action timestamps and derive the boundaries from the timing policy.

When the jersey number is unreadable after an occlusion, end the interval before identity is lost. Resume only after independently reacquiring the number. Exclude candidates with unresolved identity and list their approximate timestamps as ambiguous.

Use confidence labels:

- `verified`: number is readable in the sequence and color/team agree;
- `tracked`: number is readable immediately before or after and identity remains continuously visible;
- never include `ambiguous` candidates.

Identity confidence does not verify the event outcome. A correctly identified player can still miss, be blocked, or send the ball out of bounds.

## Player-action verification

Player visibility is not player involvement. Every retained clip must contain at least one timestamped `player_actions` record for the requested player, with identity evidence at the action itself.

For `ball-involvements`, qualifying actions include:

- receiving or controlling the ball;
- passing, carrying, dribbling, shooting, scoring, or turning it over;
- a rebound, loose-ball recovery, steal, interception, tackle, save, block, or deflection;
- the player's final touch that sends the ball out of bounds;
- a direct on-ball contest in which the player clearly pressures or challenges the ball handler.

Mere visibility, proximity to the ball, ordinary spacing, standing available for a pass, being a decoy, or appearing at one verification timestamp does not qualify. An off-ball screen, cut, closeout, press, mark, or recovery run qualifies only when the requested scope includes off-ball offense or defense; it must not be presented as a ball involvement.

Each action record must contain:

- `type`: the specific action;
- `source_seconds`: when it occurs;
- `identity_verification_seconds`: one or more nearby timestamps where the requested jersey number is readable, or from which an uninterrupted identity track reaches the action.

Identity evidence must be within 2 seconds of the action. If another same-color teammate crosses, receives the ball, or becomes the action's subject, reacquire the requested jersey number before recording another action. Do not carry a `tracked` identity across that ambiguity.

Before finalizing, ask: “If the requested player were removed from this sequence, would the recorded action still be the same?” If yes, exclude the clip unless the verified action is an intentional off-ball action within scope.

Merge overlapping or immediately adjacent intervals that describe one continuous action. Keep separate possessions as separate clips unless the user requests longer shifts.

## Zoom and player-follow framing

Keep the native full frame when the player is already large enough to identify and understand the play. When the player is too distant, use exactly `1.5` zoom and re-encode the clip:

1. Record normalized player-center coordinates (`x` and `y` from 0 to 1) at enough source timestamps to follow the player smoothly.
2. Include a point before major direction changes and after reacquiring the player from an occlusion.
3. Interpolate the crop center between points so the frame pans with the player. Keep the crop inside the source frame.
4. Prefer keeping the player near center, but shift enough to retain the ball and immediate play context when centering would hide the outcome.
5. Do not zoom when identity is uncertain, when cropping removes essential context, or merely to make the image look more dramatic.

Any zoomed clip requires `mode: precise`; stream copy cannot crop, scale, or pan. Verify first, middle, last, and direction-change frames after rendering.

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
  "clips": [
    {
      "index": 1,
      "event_type": "regular",
      "receive_seconds": 120.2,
      "release_seconds": 127.4,
      "start_seconds": 118.2,
      "end_seconds": 131.7,
      "label": "transition pass leading to teammate score",
      "confidence": "verified",
      "verification_seconds": [120.2, 127.4],
      "positive_outcome": {
        "type": "teammate_made_basket",
        "achieved_seconds": 130.2,
        "verification_seconds": [130.2]
      },
      "player_actions": [
        {
          "type": "receive",
          "source_seconds": 120.2,
          "identity_verification_seconds": [120.2]
        },
        {
          "type": "pass",
          "source_seconds": 127.4,
          "identity_verification_seconds": [127.4]
        }
      ],
      "framing": {
        "zoom": 1.5,
        "track_points": [
          {"source_seconds": 118.2, "x": 0.31, "y": 0.56},
          {"source_seconds": 123.4, "x": 0.47, "y": 0.52},
          {"source_seconds": 131.7, "x": 0.68, "y": 0.48}
        ]
      }
    }
  ]
}
```

`source_video` may instead be the verified HTTPS `c.veocdn.com` standard MP4 URL. Clip indexes must be consecutive; intervals must be ordered, positive, non-overlapping, and within the source duration. `verification_seconds`, `player_actions`, positive-outcome verification timestamps, and framing track points must fall inside the interval. Use `execution_seconds` for `goal` and `basketball_score`; use `action_start_seconds` and `action_end_seconds` for `off_ball`. `positive_outcome` is optional for non-scoring events and required for verified scoring events. Its `type` must name the concrete result, `achieved_seconds` must be at or after the player's action ends, and `verification_seconds` must include that achieved moment. For an unzoomed clip, set `framing.zoom` to `1.0` and omit `track_points`.

Every scoring entry additionally requires:

```json
{
  "event_type": "basketball_score",
  "execution_seconds": 140.0,
  "scoring_outcome": "made_basket",
  "outcome_verification_seconds": [140.8],
  "positive_outcome": {
    "type": "made_basket",
    "achieved_seconds": 140.8,
    "verification_seconds": [140.8]
  },
  "outcome_evidence": [
    {"source_seconds": 140.3, "observation": "rim_contact"},
    {"source_seconds": 140.8, "observation": "ball_below_rim_after_net"}
  ]
}
```

Use `scoring_outcome: "goal"` and `positive_outcome.type: "goal"` for soccer or futsal. Evidence timestamps must be at or after execution and inside the clip. `outcome_evidence` is required for `basketball_score`; it is optional for soccer or futsal goals. The scoring verification timestamp and positive-outcome achieved timestamp must identify the same visible result.

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

Require successful FFmpeg completion and positive FFprobe duration for every individual clip and the requested compilation. This is technical verification only. Separately inspect every `player_actions` timestamp plus the first, middle, final, direction-change, and scoring-outcome frames for player identity, actual involvement, action continuity, and accurate labels. Reject the clip if the action belongs to a teammate, even when the requested player is visible elsewhere in the frame.

Deliver:

- the output directory;
- `player-clips.json`;
- `clip-report.json`;
- all verified individual clips and, when requested, `player-compilation.mp4`;
- included clip count and total duration;
- excluded ambiguous timestamps and the reason;
- the boundary mode and its precision caveat.

Keep the textual response concise; the media files are the primary output. Do not claim exhaustive coverage unless the complete playable interval was reviewed at the requested depth.
