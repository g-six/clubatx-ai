---
name: fixture-match-report
description: Generate a coaching-focused football match report for one chosen team from a completed fixture result and saved team or player statistics. Use for post-match analysis, strengths, improvements, video-review priorities, and evidence-backed standout-player identification; do not use to enter results or import analytics.
---

# Fixture Match Report

Produce a full post-match report for the team the user names. Center every judgment on observable data, use the opponent only as comparison context, and make the video-review guidance specific enough for a coach to act on.

## Gather and verify the evidence

Use current ClubATX read-only tools when available; otherwise analyze data the user supplies.

1. Establish the exact completed fixture and selected team. Prefer a fixture ID. If only a date is given, use `find_fixtures_by_date`, then resolve ambiguity before analyzing. Use `get_fixture_match_stats` for the fixture.
2. Require a recorded final score and a statistics object containing the selected team. Match the team name case-insensitively only when there is one unambiguous canonical key; print the canonical name in the report.
3. Use both teams' statistics for comparisons even though the report is about one side. A value in isolation rarely establishes whether the selected side performed well.
4. Use `list_fixture_lineup` only when the correct home/away side is known and player identity or role is relevant. A lineup proves participation or selection, not performance.
5. Prefer player analytics and attributed match events when they are available in the supplied data or another authorized read-only source. Never infer a player's identity from jersey number, position, roster order, or an unlinked event.

If the fixture is not finalized, the chosen side is ambiguous, or the match statistics are absent, explain exactly what is missing and stop instead of fabricating a report. If team statistics are complete but player evidence is absent, complete the team report and explicitly mark standout-player identification as unsupported.

## Analyze the match

Calculate useful derived values when their denominators are known and nonzero. Label the definition used, round sensibly, and retain the source counts nearby. Useful examples include:

- result and goal margin;
- share of possession and momentum;
- selected-team advantage or deficit for completed passes and passes in each third;
- attacking-third pass share using the sum of the three pass-location counts as the denominator;
- goals per total attempt, goals per shot, inside-box attempt share, and inside/outside-box conversion;
- differences in tackles, interceptions, loose balls, dribbles, saves, corners, and fouls.

Do not call completed passes a pass-completion rate when attempted passes are unavailable. Do not equate possession with control, momentum with chance quality, total attempts with shots on target, saves with goals prevented, or event counts with successful actions unless the schema explicitly says so. Treat ratios built from small counts as fragile and say so.

When team aggregates, projected events, and player totals come from different source scopes, do not force them to reconcile. Use the canonical team statistics for team comparisons, player analytics for individual claims, and attributed events for moments and video links. Disclose meaningful discrepancies that affect a conclusion.

Build conclusions by triangulating the score with several related measures:

- For strengths, explain which phase succeeded, cite the selected team's figures and the opponent comparison, and connect the evidence to a plausible on-field pattern.
- For improvements, identify the observed symptom before suggesting a cause. Phrase tactical explanations as hypotheses to verify on video, not facts established by aggregate statistics.
- Prioritize no more than three improvement themes. Rank them by likely match impact and coachability, not by the largest raw numerical gap.
- Keep outcome and performance separate. A win can contain weak processes; a loss can contain repeatable strengths.

## Identify key players

Name a standout only when player-level evidence supports the claim. Strong evidence includes attributed goals or assists, shot and chance involvement, passing contribution, defensive actions, saves, physical output, and verified playing time. Explain what made each player stand out with exact figures or confirmed events and, when possible, role context.

- Prefer two independent signals for a strong standout claim.
- Treat source-generated player attribution and automated event detection as evidence to verify on video, especially when a player link is absent or totals disagree across sources.
- Account for playing time when comparing totals. Do not reward a larger total solely because a player played longer.
- Separate positive standouts from influential players whose errors or disciplinary events merit review.
- Do not rank players from lineup membership alone or assign team-level statistics to individuals.
- If only scorer/assister events exist, call those players decisive contributors rather than claiming they were the best overall performers.
- If evidence is insufficient, say: `Player-level performance data was not available, so the statistics do not support naming key players.` Then state which data would resolve it, such as attributed events, player metrics, or verified playing time.

## Direct the video review

Translate each major conclusion into a falsifiable viewing task. For every priority, specify:

- the phase or trigger to find, such as build-up under pressure, possession loss in the middle third, box entry, defensive transition, set piece, or shot concession;
- what to observe about spacing, body shape, support angles, scanning, decision timing, numbers around the ball, and the next action;
- the statistical clue that motivated the review; and
- what would confirm or disprove the hypothesis.

Use exact event minutes or video links only when they are present in the evidence. Otherwise give sequence categories and sampling guidance, such as reviewing every attacking-third turnover or all inside-box attempts. Never invent timestamps.

## Report shape

Write for a coach in clear football language. Use this order unless the user asks for another format:

1. **Match snapshot** — fixture, selected side, final score, outcome, and a concise performance verdict.
2. **Statistical story** — a compact selected-team-versus-opponent comparison and the most meaningful derived measures.
3. **What went well** — two to four evidence-backed findings.
4. **What needs improvement** — up to three ranked findings, each with evidence and a cautious tactical interpretation.
5. **Key players** — named standouts with evidence, or the explicit data limitation.
6. **What to watch in the recording** — a prioritized checklist tied to the findings.
7. **Next-match focus** — two or three concrete coaching objectives that are observable in training or competition.
8. **Data limits** — missing fields and claims the available data cannot support.

Quote exact figures rather than vague claims, avoid false precision, and distinguish source facts, calculated measures, and video-review hypotheses.
