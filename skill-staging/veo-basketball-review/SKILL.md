---
name: veo-basketball-review
description: Review Veo basketball footage and produce a team-focused, timestamped coaching assessment. Use when a user supplies an app.veo.co basketball match and wants film analysis, strengths, improvement priorities, practice recommendations, or configurable light, medium, or high review depth. Do not use for football analytics or database imports.
---

# Veo Basketball Review

Produce a coaching report grounded in the supplied recording. Separate what the footage visibly supports from inference, and prefer practical team-development guidance over generic basketball commentary.

## Parameters

Accept these parameters in natural language. Infer reasonable defaults rather than blocking on missing optional values.

- `url` (required): exact HTTPS `app.veo.co` match URL.
- `team`: team name plus a visual identifier such as jersey color. If omitted, assess both visible teams neutrally and say how they are identified.
- `game_start`: Veo video-clock timestamp of the opening tip, such as `1:57`. Exclude pregame footage before it.
- `depth`: `light`, `medium`, or `high`; default to `medium`.
- `output_token_budget`: optional approximate maximum for the final report. It overrides the normal report-length target but not the minimum evidence needed for a responsible assessment.
- `focus`: optional emphasis such as offense, defense, transition, rebounding, player development, or a named/numbered player.
- `timestamp_clock`: default `video`; use the Veo video clock unless the user explicitly requests elapsed game time.

Depth controls review density and report detail:

| Depth | Review approach | Normal report target |
|---|---|---|
| `light` | Scan the full playable game, inspect representative possessions from the beginning, middle, and end, and verify at least four coaching examples. | About 600–1,000 output tokens |
| `medium` | Review the full game at regular intervals, inspect at least eight representative sequences across phases and periods, and cross-check recurring patterns. | About 1,200–2,000 output tokens |
| `high` | Review the full game densely, inspect at least fifteen sequences, test whether patterns persist across lineups/game phases, and add player-number observations when reliably visible. | About 2,500–4,000 output tokens |

Treat these as quality targets, not fabricated precision. An explicit output budget controls the delivered answer, not hidden reasoning usage. If the budget is too small for essential caveats and evidence, prioritize accuracy, timestamped findings, and the top three recommendations.

## Access and footage preparation

1. Validate that the supplied URL uses HTTPS and host `app.veo.co` exactly.
2. Use the available browser workflow and the user's existing authenticated session. Navigate directly to the exact URL.
3. If sign-in is required, keep the tab available and ask the user to sign in there. Never request credentials in chat or fill passwords or one-time codes.
4. Confirm the visible match title and video duration. Do not use another match, a search result, or a guessed URL.
5. Read the loaded video's actual media source or download the video through the page's media element when supported. Downloading for local analysis is read-only; do not click Share, edit the match, upload anything, or change Veo data.
6. Use `ffprobe` when available to verify duration and stream properties. Use `ffmpeg` or equivalent to extract timestamped frames/contact sheets and short sequence views at the density required by `depth`.
7. Respect `game_start`. Express cited moments in the requested clock and make the convention explicit.

## Review method

Scan the entire playable interval, including stoppages only when they reveal substitutions, score context, or coaching organization. Use sequence-level evidence rather than isolated stills whenever judging decisions or movement.

Assess the requested team in these areas when visible:

- offensive identity, spacing, ball movement, screening, paint touches, finishing, and shot selection;
- transition offense, lane occupation, rim running, outlets, trailers, and numerical decisions;
- point-of-attack defense, closeouts, help and recovery, screen coverage, and transition organization;
- defensive and offensive rebounding responsibilities;
- communication, composure, late-game execution, and response to momentum;
- repeatable strengths and the smallest set of high-value improvements.

Cross-check a claimed recurring pattern in multiple separated sequences. Do not call something a team tendency from one possession. Distinguish:

- `Observed`: clearly visible in the footage.
- `Likely`: a cautious tactical interpretation supported by several sequences.
- `Unavailable`: team name, player identity, score, period, or statistic that cannot be verified.

Do not invent possession counts, shooting percentages, turnovers, final score, quarter boundaries, player names, or play calls. Report jersey numbers only when readable in more than one frame or sequence. If a scoreboard is clipped, distant, or overexposed, say the score is unreadable rather than guessing.

## Report

Lead with the team's overall identity and the most consequential finding. Adapt the structure to the request, normally covering:

1. overall assessment;
2. repeatable strengths;
3. offensive improvement areas;
4. defensive improvement areas;
5. transition and rebounding;
6. timestamped review moments using the Veo video clock;
7. three to five prioritized practice interventions with concrete constraints or coaching cues;
8. data-quality limitations.

Keep recommendations age-appropriate and actionable. Prefer a few connected principles over adding a large playbook. When the team is not identified, provide a neutral two-team comparison and ask which jersey color should receive the focused follow-up.

Do not claim a complete statistical analysis unless the necessary events were actually charted. A film assessment may be complete at the chosen depth while box-score statistics remain unavailable.
