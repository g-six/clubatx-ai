# ClubATX Supabase persistence

Use this reference only after Veo extraction is complete and persistence is requested.

## Destination

- Resolve the current connected Supabase project. Prefer the single active project named `clubatx`; if multiple projects could match, ask the user to choose before querying.
- The match ID supplied by the user is `public.fixtures.id` and is stored as `public.fixture_match_stats.fixture_id`.
- `public.fixtures.home_score` and `public.fixtures.away_score` are the official result fields used by the ClubATX fixture page. A complete confirmed import updates these two columns together with the analytics payload.
- `public.fixtures.half_duration_minutes` stores the nominal half duration. For a Veo import, trusted Veo period timing is authoritative. Compare the saved value with the verified Veo duration and include any required correction in the same preview and transaction.
- `public.fixtures.video_url` stores the full user-supplied Veo match URL after replacing the first `#/analysis/` route prefix with `#/`. Preserve every other character. If that route prefix is absent, store the supplied URL unchanged.
- ClubATX has no independent fixture-status column in this workflow. Downstream consumers treat both official score columns being non-null as the completion signal. A 0 is a recorded score; `null` means the fixture is still unfinalized.
- `public.fixture_match_stats` is one row per fixture. Saving the same fixture again intentionally replaces its complete payload.
- `public.fixture_player_analytics` is the only player-performance destination. It stores source identity, optional confirmed lineup/athlete links, exact playing seconds, and per-player metrics in one row per fixture side/source/jersey. Do not use the retired `fixture_player_match_stats` or `fixture_player_playing_time` tables.
- Keep every normalized Veo feed record in `fixture_match_stats.payload.key_events`, including the exact unshifted `video_time_seconds`. Also replace `public.fixture_events` with the confirmed projection of player-attributed event types supported by its current constraint. Each projected row stores the verified raw recording URL with a `#t=` media fragment set to `max(video_time_seconds - confirmed_pre_roll_seconds, 0)`; the default pre-roll is 3 seconds.
- Confirmed writes call `public.save_fixture_performance(bigint,jsonb,text,jsonb,smallint,smallint,text)` once for the function-owned destinations, update only the verified `fixtures.half_duration_minutes` value directly when needed, and replace `fixture_events` in the same explicit SQL transaction. Do not write any other `fixtures` field, `fixture_match_stats`, or `fixture_player_analytics` directly.
- If `fixture_match_stats`, `fixture_player_analytics`, `fixture_events`, or `save_fixture_performance` is absent, stop and report the missing database capability. Inspect `fixture_events` columns and check constraints before building its projection; do not create or alter schema during an import run.

## Resolve the fixture

Validate the supplied match ID as a positive integer before inserting it into SQL. Fetch one fixture and its canonical team names with the equivalent of:

```sql
select
  f.id,
  f.match_date,
  f.start_time,
  f.home_score,
  f.away_score,
  f.half_duration_minutes,
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

For every persistence run—including a retry, event refresh, side correction, athlete-link correction, or period/minute correction—read the fixture row, including `half_duration_minutes`, any existing `fixture_match_stats` row, the complete fixture/source player set, and all existing `fixture_events` rows before preparing changes.

- Do not infer completion from the presence of analytics, player statistics, or `fixture_events`.
- If both official score columns are non-null, compare them with the confirmed final score and preserve them unless the user explicitly confirms a replacement.
- If either official score is null while a trusted existing analytics payload contains a confirmed final score, identify the row as a partial import. Show the saved analytics score, the null official result, and the proposed canonical home/away repair; require the official-score confirmation and include the repair in the atomic write.
- If the saved analytics score is ambiguous, stale, invalid, or not yet confirmed as final, return to the Veo score extraction and confirmation checkpoint instead of copying it automatically.
- Imported scoresheet events are separate data. They neither finalize the fixture nor authorize deriving the official result from event counts.
- Compare `fixtures.half_duration_minutes` with the nominal half duration verified from Veo. When they differ, show both values and include the Veo value in the final confirmed write. Never retain the database value merely because it already exists, and never derive a replacement from the last event timestamp alone.

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
7. For a confirmed candidate, write the athlete's canonical database full name to `player_name` and its slug to `athlete_slug` on every event with that canonical team and jersey number. Use the same confirmed lineup identity in the consolidated player row. For an explicitly skipped mapping, retain a trustworthy source-provided event name when present and store event `athlete_slug` as `null`; otherwise keep both event fields `null`. Persist the player row with both `fixture_lineup_id` and `athlete_slug` set to `null`; unresolved attribution must not erase otherwise valid source analytics.

Every retry starts from fresh database state. If the user says fixture jersey numbers or athlete links were added, changed, or should be tried again, re-query both fixture sides and rebuild the complete mapping preview. Do not merge stale candidate rows into the refreshed result. Any revised mapping invalidates an earlier write confirmation.

Normalize whitespace and compare names case-insensitively, but escape user-provided text safely before using it in SQL. Prefer an exact normalized full-name match first. If broader partial matching is needed, show the resulting candidates and require an explicit selection.

## Build the relational event projection

Follow [veo-network-events.md](veo-network-events.md) for raw-media verification and supported type mapping. Build one intended `fixture_events` object per projectable active event using exactly these columns:

`fixture_id`, `division_team_id`, `recipient_name`, `event_type`, `minute`, `added_time`, `recipient_role`, `athlete_slug`, and `video_url`.

Use the confirmed side's division-team ID. A confirmed athlete uses the canonical database name and slug; an unlinked jersey uses `Jersey #<number>` and a null slug. Set `recipient_role` to `player`. The `video_url` must be the observed raw HTTPS `.mp4` URL with its fragment replaced by `#t=<max(exact video_time_seconds - confirmed_pre_roll_seconds, 0)>`; default to a 3-second pre-roll and never store an `app.veo.co` event route there. Do not modify the exact source `video_time_seconds` in `fixture_match_stats.payload.key_events`.

Use cumulative match minutes in both `key_events[].minute` and `fixture_events.minute`. When Veo's period clock resets, add the verified nominal duration of every completed prior period before converting seconds to the one-based minute. For a standard two-half fixture this is `floor(((period - 1) * half_duration_seconds + match_time_seconds) / 60) + 1`. Preserve exact period-local `match_time_seconds`, the period number, and explicit `added_time`; never store second-half events as minutes `1..half_duration_minutes`.

Read the full current fixture event set. A complete Veo import replaces it because `fixture_events` has no source-event ID or source namespace that can safely distinguish stale Veo rows from corrected rows. The final preview must disclose the exact deletion count, insertion count, counts grouped by canonical team and event type, skipped feed records and reasons, and that any manually curated fixture rows will also be removed. Require fresh explicit confirmation after this preview. Do not treat an earlier match/player confirmation as authorization for the replacement.

Validate the intended projection before preview:

- every row uses the confirmed fixture and one of its two division-team IDs;
- `event_type` satisfies the live table constraint;
- every recipient is non-empty and every confirmed slug exists;
- `minute` and `added_time` preserve the normalized source values;
- every period-two minute is cumulative and consistent with the verified Veo half duration;
- every `video_url` matches the single verified raw recording plus the exact numeric adjusted `#t=` fragment for the confirmed pre-roll; and
- the intended array preserves duplicate events when their source records are distinct.

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

## Canonical player array

Read [clubatx-player-stats.md](clubatx-player-stats.md) and [clubatx-playing-time.md](clubatx-playing-time.md) when player data is in scope. Build one object per confirmed `division_team_id` and jersey for the complete fixture/source replacement set. Each object carries source identity, an explicit confirmed link pair or two null link fields, exact `played_seconds` when verified, and only per-player metrics from their proper verified source.

The database function accepts the table's player fields:

`division_team_id`, `jersey_number`, `source_team`, `source_player_id`, `source_player_name`, `fixture_lineup_id`, `athlete_slug`, `played_seconds`, `tracked_minutes`, `distance_miles`, `average_speed_mph`, `top_speed_mph`, `sprints`, `high_intensity_runs`, `total_events`, `goals`, `assists`, `goal_involvements`, `conversion_rate_percent`, `shots`, `total_attempts`, `tackles`, `corners`, `free_kicks`, `throw_ins`, `fouls`, `penalty_kicks`, `goal_kicks`, `passes`, `completed_passes`, `pass_success_rate_percent`, `dribbles`, `interceptions`, and `saves`.

Leave unavailable nullable values null; never manufacture zero. The top-level `p_source` becomes every saved row's `source`. Do not include `fixture_id`, `source`, timestamps, display-only player names, or side labels inside each database player object.

## Save and verify

After the user confirms the final preview, use one Supabase SQL request containing one explicit transaction. Call the shared function exactly once, replace `fixture_events`, run pre-commit assertions, and commit only if all statements succeed:

```sql
begin;

select public.save_fixture_performance(
  <validated_match_id>,
  $veo_match$<validated_compact_match_json>$veo_match$::jsonb,
  $veo_source$veo$veo_source$,
  $veo_players$<complete_compact_player_array>$veo_players$::jsonb,
  <confirmed_home_score>::smallint,
  <confirmed_away_score>::smallint,
  $veo_url$<derived_full_veo_url>$veo_url$
);

update public.fixtures
set half_duration_minutes = <verified_veo_half_duration>::smallint
where id = <validated_match_id>
  and half_duration_minutes is distinct from <verified_veo_half_duration>::smallint;

delete from public.fixture_events
where fixture_id = <validated_match_id>;

insert into public.fixture_events (
  fixture_id, division_team_id, recipient_name, event_type,
  minute, added_time, recipient_role, athlete_slug, video_url
)
select
  fixture_id, division_team_id, recipient_name, event_type,
  minute, added_time, recipient_role, athlete_slug, video_url
from jsonb_to_recordset(
  $veo_events$<complete_confirmed_fixture_event_array>$veo_events$::jsonb
) as e(
  fixture_id bigint,
  division_team_id bigint,
  recipient_name text,
  event_type text,
  minute integer,
  added_time integer,
  recipient_role text,
  athlete_slug text,
  video_url text
);

-- Add count, side, and raw-URL assertions that raise on mismatch.
commit;
```

Before executing, confirm that each dollar-quote delimiter does not occur in its enclosed value. The transaction atomically:

- updates only `fixtures.home_score`, `fixtures.away_score`, `fixtures.video_url`, and the verified Veo `fixtures.half_duration_minutes` value;
- upserts the complete `fixture_match_stats.payload`;
- deletes and replaces `fixture_player_analytics` rows for the confirmed fixture and source when `p_players` is non-null; and
- deletes and replaces the confirmed fixture's complete `fixture_events` projection.

For an event-only or match-only correction, pass `p_players = null` so player rows are preserved. Never pass a partial player array. An empty array clears every player row for that fixture/source and is allowed only after the final preview explicitly identifies and the user confirms that destructive scope. For a player-only correction, pass `p_match_stats = null` to preserve the saved payload, pass the complete player replacement array, preserve the confirmed non-null official score, and use `p_video_url = null` unless a URL change is also confirmed.

For a later event-link-marker correction where the saved event rows, raw recording URL, and exact source `key_events[].video_time_seconds` have already been verified, use a narrower guarded transaction that updates only `public.fixture_events.video_url`. Before confirmation, show the current event count, parseable-marker count, current marker range, proposed pre-roll, proposed marker range, and sample current/proposed URLs. Assert the expected fixture row count and current URL form before updating, derive every new marker deterministically, clamp at zero, assert the updated count and final raw-URL form, and commit only if every assertion passes. Preserve `fixture_match_stats`, `fixture_player_analytics`, scores, sides, recipients, types, minutes, athlete links, and every non-URL event field. If any exact source time cannot be recovered or the existing marker does not represent that source time under the known prior rule, stop and rebuild the complete projection instead.

For a later period/minute correction, use one guarded transaction that updates `fixtures.half_duration_minutes`, every affected `fixture_match_stats.payload.key_events[].minute`, and the corresponding `fixture_events.minute` values together. Preview current and proposed half duration, per-period source and cumulative minute ranges, and affected row counts. Identify projected period rows from verified event identity or exact video markers, not from the currently wrong minute alone. Preserve periods, exact `match_time_seconds`, exact `video_time_seconds`, URLs, scores, sides, recipients, athlete links, and all unrelated fields. Assert expected counts and ranges before and after mutation and roll back on any mismatch.

Do not call `save_fixture_scoresheet`, substitute multiple REST calls, or write the retired player tables. If the function or transaction-capable SQL operation is unavailable, stop before mutation. A failure after `begin` must roll back the function call and event replacement together.

After the call completes, run filtered read-only queries for the same fixture:

1. Read `fixtures.home_score`, `fixtures.away_score`, `fixtures.half_duration_minutes`, and `fixtures.video_url`.
2. Read the single `fixture_match_stats.payload` and compare it as JSONB with the intended complete payload.
3. Read `fixture_player_analytics` filtered by both fixture ID and source, ordered by `division_team_id, jersey_number`.
4. Require the stored player-row count to equal the complete intended replacement count. Compare every intended field, including nulls, every exact `played_seconds`, and every link pair. Also require no extra row for that fixture/source.
5. Require linked rows to match the confirmed `fixture_lineups` composite identity and unresolved rows to have both link fields null.
6. Read every `fixture_events` row for the fixture and compare it to the intended projection as a multiset (`EXCEPT ALL` in both directions or an equivalent duplicate-preserving comparison).
7. Require the saved event count and grouped side/type counts to match, every event URL to use the verified raw `.mp4#t=<max(exact source seconds - confirmed pre-roll, 0)>` form, and zero event URLs to use `app.veo.co`.
8. Require the saved half duration to equal Veo's verified nominal duration and every normalized and projected period-two minute to be cumulative rather than reset.

Both official scores must be non-null and exactly match the confirmed canonical home/away result; zero is valid. The video URL must exactly equal the derived value when it was part of the write. Database numerics may serialize as strings, so compare exact numeric values without rounding beyond source precision.

If any comparison fails, or analytics exist while either official score is null, report the import as incomplete and do not claim success or finalization. After a successful replacement, state how many prior fixture rows were removed and that recovery requires a database backup. Never log, print, or request Supabase secrets.
