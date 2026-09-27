# ClubATX exact playing-time persistence

Read this reference when a verified Veo response exposes exact player `secondsPlayed` and the user asks to persist playing time.

## Destination and source rules

- Store exact seconds in `public.fixture_player_playing_time`; do not store them in `fixture_match_stats.payload` or replace `fixture_player_match_stats.tracked_minutes`.
- The compatible schema is introduced by the `track_fixture_player_playing_time` migration. Check that the table exists before preparing a write.
- Each row is identified by `(fixture_id, fixture_lineup_id)` and is also unique by `(fixture_id, athlete_slug)`.
- Preserve the verified aggregate `secondsPlayed` integer exactly. The UI may display `Math.round(played_seconds / 60)`, but the database value remains exact seconds.
- When the response contains period rows and an aggregate row such as `drill: "ALL"`, use the aggregate row only. Never add it to the component rows.
- Never derive exact seconds by multiplying rendered tracked minutes by 60.
- Omitted rows are preserved. Do not delete earlier playing-time rows without an explicit destructive request and confirmation.

## Resolve the athlete link

1. Determine the confirmed canonical fixture side that owns the exact-time response.
2. Require one unique non-negative integer jersey number per aggregate source row.
3. Refresh `public.fixture_lineups` using the confirmed `fixture_id`, side's `division_team_id`, and `jersey_number`. Select `id`, `athlete_slug`, `player_name`, and `jersey_number`.
4. Treat zero matches, duplicate jerseys, and null athlete slugs as unresolved. Never choose a player from the other fixture side or infer an athlete from the jersey alone.
5. Show every proposed jersey-to-lineup-to-athlete mapping and require confirmation immediately before writing.

Skip unresolved rows and report them. A confirmed row uses the lineup `id` as `fixture_lineup_id` and its exact `athlete_slug`.

## Validate and preview

Require each `played_seconds` value to be a non-negative integer no greater than 86400. Verify the response against the rendered table with `Math.round(played_seconds / 60)` for at least three jerseys and preferably every available row. A mismatch is a data-quality issue: show both values and stop the affected playing-time write.

Preview the source team, exact row count, linked write count, skipped jerseys, every confirmed mapping, exact seconds, and rounded display minutes. State that `public.fixture_player_playing_time` will be upserted and whether any other confirmed import data is part of the same transaction.

## Save and verify

Use the Supabase SQL connector. Include the rows in the complete import's atomic statement when practical. For a later playing-time-only correction, perform one upsert statement after the fixture, side, and mappings have been reconfirmed:

```sql
insert into public.fixture_player_playing_time (
  fixture_id,
  fixture_lineup_id,
  athlete_slug,
  played_seconds,
  source,
  updated_at
)
values (...)
on conflict (fixture_id, fixture_lineup_id) do update
set
  athlete_slug = excluded.athlete_slug,
  played_seconds = excluded.played_seconds,
  source = excluded.source,
  updated_at = now();
```

Use a short lower-snake-case source such as `veo`. Read back only the confirmed fixture's rows and join them to `fixture_lineups` on the complete `(fixture_id, fixture_lineup_id, athlete_slug)` identity. Verify the returned count, every athlete slug, exact `played_seconds`, and source. Report rounded minutes only as a display check, not as the persisted value.
