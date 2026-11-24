# ClubAtx fixture publishing

Use this procedure only when the user asks to save reviewed events or video to
a ClubAtx fixture. It extends the local review; it does not require a full Veo
Analytics import or fabricated match statistics. Carry forward user corrections
throughout review and publishing without requesting them again.

## Resolve the match and reconcile the review

- Resolve relative dates in the user's match context and timezone. Read the
  exact fixture and verify both teams, date, home/away IDs and existing result.
  Do not select a fixture from a filename alone or assume jersey colors.
- Reuse the user's verified team/color mapping. For each shot and goal, review
  the shooter in the dense lead-up, strike and aftermath for a readable jersey.
  Retain that team-scoped jersey even when no player account is linked. Resolve
  the player from an explicit verified mapping, then the exact fixture lineup,
  then a unique matching team-roster link. Conflicting or ambiguous mappings
  remain unresolved. Never infer identity from appearance or assign an unknown
  shooter to an available lineup player. Report any shots that still lack a
  verified jersey or player rather than presenting team-only attribution as a
  completed player match.
- On a requested re-import, reuse saved visual evidence when it belongs to the
  unchanged recording; revisit shooter numbers and unresolved links under the
  updated workflow. Extraction alone is not a new review. Read back current
  events and admin links before deriving the patch. Keep existing event IDs,
  source identities, video anchors and user corrections.
- Read existing events, fixture video, finalization/clock state, lineups and
  relevant analytics before writing. Save a before-state and proposed changes.
- Preserve the official result and existing goal/card/assist records. A partial
  video review may locate fewer goals than the official result. Report the gap;
  never manufacture events, players or times to reconcile it.
- Check possible goals for offensive fouls and pre-shot stoppages. Keep explicit
  user-confirmed disallowances and counted goals in the review with their source.
  An attacking foul followed by a finish is not a new counted goal.
- Import confirmed events within the requested scope. Keep unresolved chances
  separate from confirmed shots/goals. A two-shot rebound sequence must remain
  described as a sequence unless separate attempts have verified timestamps.
- Reconcile located goals with existing records only when the identity is
  supported. Do not arbitrarily attach a finish to one of several untimed goals.
  A complete group of verified clips may match a complete group of otherwise
  indistinguishable untimed goals for the same team and scorer/jersey when the
  counts agree. Pair deterministically and record that basis; every time comes
  from its clip, and ID order is not evidence of official scoring chronology.
  If a scorer group's counts disagree or identities conflict, leave the match
  unresolved. Different players sharing a roster number remain ambiguous even
  when their jersey is readable.
  When publishing shot clips while official goals already exist, a scoring
  attempt may be a `shot` with a scoring-outcome note; do not insert another
  `goal` or increment the score. Explain that these categories overlap.

## Keep display time, event time and playback start separate

Visually locate the first kickoff with dense frames, refining to about 0.1 seconds
when needed. Record its exact video offset and evidence. Each new match needs its
own offset; never reuse the previous match's kickoff.

Let `K` be the first-kickoff video seconds and `V` the immutable event video seconds:

```text
display_elapsed_seconds = max(V - K, 0)
display_whole_seconds   = floor(display_elapsed_seconds)
display_minute         = floor(display_whole_seconds / 60)
event_play_start       = max(V - 2.2, 0)
```

- Kickoff is 0:00. By default this is running elapsed time, including stoppages
  and halftime. Disclose that basis; do not silently subtract breaks or invent
  the official futsal stopped clock. If the user requests actual playing time,
  use observed period/clock synchronization instead.
- Apply the same baseline to every event type with a verified video timestamp,
  including shots, scoring finishes, fouls, saves, cards and restarts. Populate
  the supported display minute so Play-by-Play does not show TBD for timed events.
  With the existing fixture-event convention, store `minute = display_minute`,
  `added_time = 0`, and `game_clock_seconds = display_whole_seconds`, documenting
  that these review rows use running kickoff-relative time. Verify the current
  service contract before writing. Keep report `match_clock` null unless the
  official clock is actually known; retain running display time separately.
- Original scoresheet events without a verified video moment remain untimed.
  Do not borrow a neighboring event's time or infer timing from goal order.
- When an admin links a reviewed attempt to an existing goal, the goal's
  recorded minute and added time take precedence for that linked attempt.
  Copy that match time without changing the original video timestamp or
  subtracting pre-roll from the displayed minute. An untimed goal can receive
  the reviewed attempt's time as part of the explicit link; keep this source
  distinction in the audit. Later goal-minute corrections should also be
  reflected in the linked attempt's display.
- Preserve `V` with subsecond precision in durable source metadata, the exported
  review/import manifest, or event commentary. Also retain `K`, source identity
  and the elapsed-time basis. Respect field lengths and do not discard evidence
  descriptions just to repeat metadata.
- Each event Play URL uses the exact verified raw MP4 plus `#t=event_play_start`.
  Use **2.2 seconds of pre-roll** unless the user requests a different allowance.
  Pre-roll changes playback only: preserve `V`, display times and kickoff.
- Recalculate links from immutable `V` on reruns. Never subtract the allowance
  again from an already adjusted URL, derive `V` from a rounded minute, or use
  a pre-rolled URL as an exact event timestamp.

Example: with kickoff `K = 90` and event `V = 150.25`, display elapsed is 1:00.25
(minute 1; whole seconds 60), and Play starts at raw video `#t=148.05`. Repeating
the update must produce that same link, not a second subtraction.

## Attach the correct Veo source

Keep three URL roles distinct:

1. **Source identity:** retain the original supplied `app.veo.co` match URL in
   provenance. Read referenced chats before using their source links.
2. **Match video:** set the fixture's `video_url` to the exact verified HTTPS
   standard-player MP4, without a fragment. This enables the Match video button.
3. **Event Play:** use that same MP4 with the per-event pre-roll fragment above.

Use the exact match player's observed source or previously verified download
provenance connecting the local MP4 to that source. Do not guess CDN paths,
substitute a highlight, or use the Veo navigation page as the raw recording.
Preserve host/path/case/encoding and signed query parameters. Verify the media
is available and matches the recording; a successful URL syntax check alone
does not establish match identity. Do not download the entire recording again
merely to validate a link. If the source expires, re-observe it through the
authorized Veo session.

## Save through the available authorized interface

Prefer ClubAtx tools/API and inspect their actual supported fields and event
types. Some connectors only support scheduling or roster-linked scoresheet
events and cannot import shots, video links or finalized-fixture review rows.
Do not call an unsupported endpoint as if it succeeded.

When the requested write needs an existing administrative data interface, use
it only within the user's authorized scope and the host's permissions. Inspect
the live schema, constraints and triggers first; installed migrations may lag.
Use the applicable database skill when accessing a database. Never package
credentials, hardcode a project/fixture/team ID, weaken access controls or
change production schema just to bypass an unsupported import.

For an event-only import, use the supported event store; do not manufacture a
complete `fixture_match_stats` payload with zero-valued unknown statistics.
Preserve unrelated existing analytics and player data. Use a source marker and
stable event identity based on fixture, recording, event type and original `V`
to avoid duplicates. Prefer a true source-event key; use a supported idempotency
key when that is the available contract. Do not replace all fixture events.

Use a transaction or the service's atomic write operation where available.
Lock/check the expected before-state and abort on concurrent changes. Save only
the requested events/video/times; preserve official scores, finalization, clock
state, player attribution, lineups and unrelated event fields. In particular,
an allowance-only correction changes event URLs, not match times or Match video.
Retain before/after audit artifacts and compare the intended rows after saving.

## Verify completion

- Read back every affected event. Compare team, type, status/provenance,
  kickoff-relative time and exact `V - 2.2` URL; confirm no duplicate goal rows.
- Confirm shots and goals group under their verified team/jersey, with the
  linked player when uniquely supported. Unknown-player events must still
  display the verified jersey number. Preserve existing named scorers and
  card recipients; do not erase them during a review import.
- Ensure all official goals and yellow/red cards appear in **Key events**,
  including entries whose video moment is still unknown. Match review clips
  onto existing official goals when supported instead of leaving a scoring
  finish visible only as an anonymous shot. Do not let a separate live-feed
  snapshot hide the official goal/card timeline or discard untimed entries.
- Compare original events and unrelated fixture/player data against the
  before-state. Verify the official score and finalization are unchanged.
- Read back the full Match video URL, with no event fragment.
- Inspect the real fixture page for Match video and Play-by-Play. Verify the
  event labels and Play targets when an eligible signed-in session is available.
  Respect normal team sign-in gating; do not bypass it or send magic-link emails
  to other people. If gated, report saved-data verification separately from
  authenticated UI checks rather than claiming an unseen playback succeeded.
- Report the fixture link, imported/updated counts, timing basis, pre-roll and
  any untimed original events or unresolved scoring gaps concisely.

## Fixture player experience

An authenticated admin can use **Mark key event** on the fixture page to match
a marked shot/scoring finish to an existing same-team goal. Existing goals offer
**View key event** instead of creating another goal. This attaches the original
shot playback URL, applies the linked goal's authoritative minute and keeps the
official result unchanged. Verify the saved pair and copied minute. Do not
automatically convert all reviewed scoring finishes into additional goals.
Use the server-verified admin controls when available; platform admins can
manage fixture teams, while organization admins are restricted to their own
organization's team. A client-visible admin flag alone is not authorization.

Place the admin shot-to-goal selector and **Mark key event** action inside the
clip modal so attribution can be set while watching. Keep these controls within
the fullscreen panel and accessible by scrolling on small screens. Reuse server
permission checks; changing an import cannot enable admin controls by itself.

The preferred fixture experience opens both Match video and each event Play
action in a video modal on the current page, preserving the supplied MP4 URL
and event pre-roll. Reuse the existing authorized viewer flow; a modal does
not grant access to a signed-out viewer. Apply the supplied fragment time to the
media currentTime after metadata loads; do not rely solely on #t support, since
mobile Safari may begin at 0:00. Verify the resulting seek without changing the
original event timestamp or subtracting pre-roll a second time. Closing pauses/unmounts playback and
restores focus to the triggering action.

On mobile devices, request fullscreen landscape from the opening user gesture
when supported. Release orientation locks and fullscreen on close/unmount and
handle a close while those requests are pending. Screen-orientation locking is
browser-dependent; keep a usable modal and native controls if the browser
rejects it, and do not claim a physical-device rotation was tested from desktop
emulation alone. Include both Match video and event actions in UI verification.

These are viewer requirements, not fields that can be enabled by SQL. If the
existing website lacks them, report that boundary and implement the necessary
website change only within the user's authorized scope. Do not claim a plugin
instruction update has itself deployed or changed the fixture-page player.
