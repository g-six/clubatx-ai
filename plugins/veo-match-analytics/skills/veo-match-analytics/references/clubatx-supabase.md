# ClubATX Supabase persistence

Use this reference only after Veo extraction is complete and persistence is requested.

## Destination

- Resolve the current connected Supabase project. Prefer the single active project named `clubatx`; if multiple projects could match, ask the user to choose before querying.
- The match ID supplied by the user is `public.fixtures.id` and is stored as `public.fixture_match_stats.fixture_id`.
- `public.fixtures.home_score` and `public.fixtures.away_score` are the official result fields used by the ClubATX fixture page. A complete confirmed import updates these two columns together with the analytics payload.
- `public.fixtures.video_url` stores the full user-supplied Veo match URL after replacing the first `#/analysis/` route prefix with `#/`. Preserve every other character. If that route prefix is absent, store the supplied URL unchanged.
- ClubATX has no independent fixture-status column in this workflow. Downstream consumers treat both official score columns being non-null as the completion signal. A 0 is a recorded score; `null` means the fixture is still unfinalized.
- `public.fixture_match_stats` is one row per fixture. Saving the same fixture again intentionally replaces its complete payload.
- Individual Veo events belong in the payload's `key_events` array. Do not insert them into `public.fixture_events`; that table represents manually curated result events and has a narrower event-type model.
- If `fixture_match_stats` does not exist, stop and tell the user that the repository migration `supabase/migrations/20260921190951_fixture_match_stats.sql` must be applied. Do not create or alter schema during an import run.

## Resolve the fixture

Validate the supplied match ID as a positive integer before inserting it into SQL. Fetch one fixture and its canonical team names with the equivalent of:

```sql
select
  f.id,
  f.match_date,
  f.start_time,
  f.home_score,
  f.away_score,
  f.video_url,
  home_ts.team as home_team,
  away_ts.team as away_team
from public.fixtures as f
left join public.division_teams as home_dt on home_dt.id = f.home_division_team_id
left join public.team_seasons as home_ts on home_ts.id = home_dt.team_season_id
left join public.division_teams as away_dt on away_dt.id = f.away_division_team_id
left join public.team_seasons as away_ts on away_ts.id = away_dt.team_season_id
where f.id = <validated_match_id>;
```

Require exactly one row and non-null home and away team names. Use those names, not Veo aliases, as the two JSON keys after the user confirms each assignment.

## Audit completion and repair partial imports

For every persistence run—including a retry, event refresh, or athlete-link correction—read both the fixture row and any existing `fixture_match_stats` row before preparing changes.

- Do not infer completion from the presence of analytics, player statistics, or `fixture_events`.
- If both official score columns are non-null, compare them with the confirmed final score and preserve them unless the user explicitly confirms a replacement.
- If either official score is null while a trusted existing analytics payload contains a confirmed final score, identify the row as a partial import. Show the saved analytics score, the null official result, and the proposed canonical home/away repair; require the official-score confirmation and include the repair in the atomic write.
- If the saved analytics score is ambiguous, stale, invalid, or not yet confirmed as final, return to the Veo score extraction and confirmation checkpoint instead of copying it automatically.
- Imported scoresheet events are separate data. They neither finalize the fixture nor authorize deriving the official result from event counts.

## Confirm the official result

After the home and away mappings are confirmed, show the current database `home_score` and `away_score` and the proposed final score from the trusted completed Veo analytics. Require explicit confirmation before setting or replacing the official result.

- Treat two null score columns as no official result.
- If either stored score is non-null, show the existing result and require explicit replacement confirmation when it differs.
- Require non-negative safe integers for both proposed scores and require each to equal the corresponding canonical team's `events.goals` value.
- Do not infer a final result from a playback-position scoreboard, title order, raw event count, or analytics still marked as processing.
- Event-only and athlete-attribution corrections preserve the current official score unless the user separately confirms a score change.

## Normalize the fixture video URL

Use the original validated `https://app.veo.co` URL supplied by the user, not a browser redirect or a reconstructed URL. Replace the first exact `#/analysis/` substring with `#/` and leave all remaining characters unchanged. For example, `https://app.veo.co/matches/example/#/analysis/abc?foo=1` becomes `https://app.veo.co/matches/example/#/abc?foo=1`. If `#/analysis/` is absent, the normalized value is the original URL. Show the current and proposed `fixtures.video_url` values in the final preview and include the proposed value in the same write confirmation as the analytics and official score.

## Resolve athletes for jersey-bearing analytics

Run this workflow after the user confirms the home/away mapping and before building the final payload.

1. Collect the distinct `(canonical team, jersey_number)` pairs from `key_events`, the rendered player-statistics table, and verified exact playing-time rows where `jersey_number` is non-null. Keep identical jersey numbers on opposing teams separate.
2. Query `public.fixture_lineups` for the confirmed fixture and corresponding division team to find current `id`, `player_name`, `athlete_slug`, and jersey matches. Present all unique linked matches and every missing, ambiguous, or unlinked jersey in one grouped preview. A unique lineup match is a candidate, not proof. The user may confirm using all shown current lineup links in one batch, correct individual mappings, or explicitly leave any or all jerseys unlinked.
3. If the user provides a name instead of accepting a current linked lineup row, search `public.athletes` using that user-confirmed name. Select only `slug`, `first_name`, `last_name`, and `date_of_birth`; do not fetch or display contact or address fields.
4. When exactly one athlete matches, show the canonical full name and athlete slug and ask the user to confirm the link.
5. When multiple athletes match, list every candidate with full name, date of birth (or `unknown` when null), and slug. Ask the user to select one exact candidate. Never choose based on result order, age, team, or similarity alone.
6. When no athlete matches, ask the user to correct the name or explicitly leave that team/jersey unlinked. Do not create or edit an athlete record during this import.
7. For a confirmed candidate, write the athlete's canonical database full name to `player_name` and its slug to `athlete_slug` on every event with that canonical team and jersey number. Use the same confirmed lineup identity for matching player-stat and exact playing-time rows. For an explicitly skipped mapping, retain a trustworthy source-provided event name when present and store event `athlete_slug` as `null`; otherwise keep both event fields `null`. Player-stat or exact playing-time rows that require a relational athlete link are skipped and reported when unlinked.

Every retry starts from fresh database state. If the user says fixture jersey numbers or athlete links were added, changed, or should be tried again, re-query both fixture sides and rebuild the complete mapping preview. Do not merge stale candidate rows into the refreshed result. Any revised mapping invalidates an earlier write confirmation.

Normalize whitespace and compare names case-insensitively, but escape user-provided text safely before using it in SQL. Prefer an exact normalized full-name match first. If broader partial matching is needed, show the resulting candidates and require an explicit selection.

## Canonical payload

The payload contains exactly `match`, `teams`, and `key_events` at the top level. Read [veo-network-events.md](veo-network-events.md) for extraction and normalization rules.

```json
{
  "match": {
    "title": "Database Home Team vs. Database Away Team",
    "sport": "football",
    "score": {
      "Database Home Team": 0,
      "Database Away Team": 0
    }
  },
  "teams": {
    "Database Home Team": {
      "possession_percent": 0,
      "completed_passes": 0,
      "passes_by_third": {
        "defensive_third": 0,
        "middle_third": 0,
        "attacking_third": 0
      },
      "events": {
        "goals": 0,
        "shots": 0,
        "total_attempts": 0,
        "corners": 0,
        "free_kicks": 0,
        "goal_kicks": 0,
        "throw_ins": 0,
        "fouls": 0,
        "tackles": 0,
        "dribbles": 0,
        "interceptions": 0,
        "loose_balls": 0,
        "saves": 0
      },
      "attempt_locations": {
        "inside_box_attempts": 0,
        "inside_box_goals": 0,
        "outside_box_attempts": 0,
        "outside_box_goals": 0
      },
      "momentum_percent": null
    },
    "Database Away Team": {
      "possession_percent": 0,
      "completed_passes": 0,
      "passes_by_third": {
        "defensive_third": 0,
        "middle_third": 0,
        "attacking_third": 0
      },
      "events": {
        "goals": 0,
        "shots": 0,
        "total_attempts": 0,
        "corners": 0,
        "free_kicks": 0,
        "goal_kicks": 0,
        "throw_ins": 0,
        "fouls": 0,
        "tackles": 0,
        "dribbles": 0,
        "interceptions": 0,
        "loose_balls": 0,
        "saves": 0
      },
      "attempt_locations": {
        "inside_box_attempts": 0,
        "inside_box_goals": 0,
        "outside_box_attempts": 0,
        "outside_box_goals": 0
      },
      "momentum_percent": null
    }
  },
  "key_events": [
    {
      "source_event_id": "veo-event-id",
      "sequence": 0,
      "period": 1,
      "minute": 1,
      "added_time": null,
      "match_time_seconds": 60,
      "video_time_seconds": 129,
      "team": "Database Home Team",
      "source_team": "Veo home-team label",
      "event_type": "pass",
      "status": null,
      "jersey_number": 25,
      "player_name": null,
      "athlete_slug": null,
      "attribution": "ai"
    }
  ]
}
```

The numeric zeros above illustrate numeric types only. Never use them as defaults for missing Veo data. The example uses null momentum to illustrate the sole nullable team metric; it is valid only when a trusted match response explicitly reports that momentum data is unavailable and the rendered analytics exposes no momentum section. Under that condition both teams must use `null`. Do not use null for a still-processing, access-gated, ambiguous, or unobserved momentum source, and never substitute possession or another metric.

Validate before saving:

- The two team keys are exactly the confirmed canonical database names and appear identically in `match.score`.
- Counts are non-negative safe integers, including every `passes_by_third` value. Percentages other than the explicitly unavailable momentum exception are finite numbers from 0 through 100. If Veo displays pass-location percentages, convert them to counts only when the source exposes a reliable denominator; otherwise stop and request the missing counts rather than storing percentages.
- Each score equals that team's `events.goals`.
- `shots` does not exceed `total_attempts`.
- Inside/outside goals do not exceed their corresponding attempts.
- The two possession percentages total 100 within 0.1.
- When momentum is available, both momentum percentages are finite numbers from 0 through 100 and total 100 within 0.1. When a trusted match response explicitly reports momentum unavailable and no rendered momentum section exists, both values are `null`; never accept one null and one numeric value.
- `key_events` is a complete array, including zero events only when the trusted response explicitly returns a complete empty result. Each object contains exactly the fields documented in `veo-network-events.md`.
- Event `sequence` values are unique, contiguous, and start at zero. Stable non-null `source_event_id` values are unique.
- Every event `team` is one of the two canonical team keys. Each `source_team` agrees with the confirmed Veo-to-database mapping.
- Event numeric values satisfy the nullability and ranges in the event reference; strings are normalized without inventing unavailable attribution.
- Each non-null `athlete_slug` exists in `public.athletes`, and `player_name` is the selected athlete's canonical database name. All events sharing a canonical team and jersey number use the same athlete mapping; opposing teams are validated independently.
- The final preview lists every distinct team/jersey mapping, including mappings the user explicitly left unlinked.
- Do not save partial payloads and do not invent unavailable values.

The rendered team metrics and event feed are separate source scopes. `teams.*.events.shots` and `total_attempts` come from the rendered team table or verified equivalent export; they are not recomputed from `key_events`. An event-feed count may legitimately differ. Preserve both, show the exact discrepancy in the preview, and do not change records or team metrics solely to force equality.

When adding events to an existing row, preserve its validated `match` and `teams` objects and replace the whole `key_events` array. Never append without reading the saved row first. The repository's HTTP match-stats validator may lag this extended JSONB shape, so this import workflow uses the SQL connector and verifies the saved JSON directly.

## Save and verify

After the user confirms the final preview, use the Supabase SQL connector to perform one atomic statement that upserts the analytics payload and updates only the official home and away score columns:

```sql
with saved_stats as (
  insert into public.fixture_match_stats (fixture_id, payload, updated_at)
  values (
    <validated_match_id>,
    $veo$<validated_compact_json>$veo$::jsonb,
    now()
  )
  on conflict (fixture_id) do update
  set payload = excluded.payload,
      updated_at = now()
  returning fixture_id, payload, created_at, updated_at
),
saved_fixture as (
  update public.fixtures
  set home_score = <confirmed_home_score>,
      away_score = <confirmed_away_score>,
      video_url = $veo_url$<derived_full_veo_url>$veo_url$
  where id = <validated_match_id>
  returning id, home_score, away_score, video_url
)
select
  saved_stats.fixture_id,
  saved_stats.payload,
  saved_stats.created_at,
  saved_stats.updated_at,
  saved_fixture.home_score,
  saved_fixture.away_score,
  saved_fixture.video_url
from saved_stats
join saved_fixture on saved_fixture.id = saved_stats.fixture_id;
```

Before executing, confirm that each chosen dollar-quote delimiter does not occur in the value it encloses. Execute exactly one mutating statement. When linked player statistics are also confirmed, extend this statement with an input-values CTE and a `saved_player_stats` upsert CTE following [clubatx-player-stats.md](clubatx-player-stats.md), and return its saved-row count alongside the fixture result. Do not issue a separate player write that could leave only half of a confirmed combined import committed.

If the SQL connector or another transaction-capable database operation is unavailable, do not approximate this with separate analytics and fixture REST mutations. Stop before writing so the workflow cannot leave another analytics-present/score-null partial import.

Require the statement to return exactly one joined fixture row; zero rows means the fixture update failed and must not be reported as success. Then run separate filtered `select` queries by the same fixture ID and compare the returned JSON, official scores, exact `video_url`, and any player rows with the complete intended import. Require both score values to be non-null (while accepting numeric zero) and exactly equal to the confirmed final score. Require `video_url` to exactly equal the derived full Veo URL. If the analytics payload exists but either official score is null or mismatched, call the result an incomplete import and do not say the fixture is final, complete, or successfully imported. Report a `video_url` mismatch as failed verification rather than claiming the import succeeded.

Never log, print, or request Supabase secrets. Never broaden the write beyond the confirmed analytics row, the two official-score columns and `video_url` on the confirmed fixture row, and any explicitly previewed and confirmed player-stat or exact playing-time rows.
