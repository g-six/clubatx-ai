# ClubATX AI

Codex plugins and reusable agent workflows for ClubATX operations.

This repository is a Codex marketplace for ClubATX agent skills. It distributes plugins for importing confirmed Veo analytics and securely recording completed fixture results.

## Included plugins

### Veo Match Analytics

`veo-match-analytics` can:

- open an `https://app.veo.co/...` match in the user's existing browser session;
- extract rendered match, team, player, and event analytics;
- map Veo teams to the canonical ClubATX fixture teams;
- reconcile the fixture half duration with verified Veo timing and normalize period-local clocks to cumulative match minutes;
- resolve jersey-bearing analytics against the current fixture lineup;
- preview every proposed database mutation and request confirmation;
- atomically save the analytics payload, complete supported player-event projection with raw-video timestamp links, official score, and consolidated player statistics; and
- read the saved rows back and verify the complete import.

The workflow explicitly detects partial imports. Saved analytics or imported events do not finalize a ClubATX fixture: both `fixtures.home_score` and `fixtures.away_score` must be non-null and match the confirmed result. A numeric zero is a valid recorded score.

### Enter Fixture Result

`enter-fixture-result` can:

- find the exact completed fixture and inspect its existing scoresheet;
- resolve named event recipients against ClubATX athlete records;
- preview append or replacement changes and the calculated final score;
- require explicit approval before saving; and
- use the OAuth-protected fixture-result MCP endpoint remotely or the credential-backed local runner as a fallback.

## Requirements

- Codex CLI or the Codex experience in the ChatGPT desktop app with plugin support.
- Access to the target Veo match. Sign-in happens in the user's browser; credentials must never be pasted into chat.
- A configured Supabase connection for the ClubATX project with the permissions required by the requested import.
- A transaction-capable SQL operation for persistence. The plugin will stop instead of splitting a complete import into independent analytics and score writes.

## Install

Add this GitHub repository as a marketplace:

```sh
codex plugin marketplace add g-six/clubatx-ai --ref main
```

Install the plugin:

```sh
codex plugin add veo-match-analytics@clubatx-ai
```

To install the fixture-result workflow instead:

```sh
codex plugin add enter-fixture-result@clubatx-ai
```

Then start a new Codex task so the installed skill is loaded. In the ChatGPT desktop app, you can also open the Plugins Directory, select the **ClubATX AI** marketplace, and install either plugin.

To receive repository updates later:

```sh
codex plugin marketplace upgrade clubatx-ai
codex plugin add veo-match-analytics@clubatx-ai
```

## Use

Provide the exact Veo match URL and the ClubATX fixture ID when known. For example:

> Import the completed analytics from `https://app.veo.co/...#/analysis/` into ClubATX fixture 74.

Before any write, the workflow will present and require confirmation of:

1. the ClubATX fixture;
2. the Veo-to-database home and away team assignments;
3. the current and proposed official score;
4. athlete mappings for every relevant team and jersey number; and
5. the exact tables and rows that will be changed.

The plugin does not ask for or expose database keys, passwords, browser cookies, or Veo credentials.

## Persistence model

The workflow writes only the confirmed fixture-scoped data:

| Destination | Purpose |
| --- | --- |
| `public.fixture_match_stats` | Canonical match and team analytics plus the complete ordered Veo event feed |
| `public.fixture_events` | Supported player events with raw `.mp4#t=<seconds>` links using a confirmed 3-second pre-roll by default |
| `public.fixtures.home_score` | Confirmed official home score |
| `public.fixtures.away_score` | Confirmed official away score |
| `public.fixture_player_analytics` | Consolidated player statistics, exact seconds, source identity, and optional confirmed athlete links |

It does not use analytics events to infer athlete identity, and it does not modify teams, athletes, lineups, or unrelated fixture fields. A confirmed complete import replaces the fixture's existing `fixture_events` projection in the same transaction, so the preview explicitly identifies the destructive scope—including any manually curated rows—before requesting final approval. Event rows alone are not proof that a fixture is finalized.

## Repository layout

```text
.
├── .agents/plugins/marketplace.json
└── plugins/
    ├── enter-fixture-result/
    │   ├── .codex-plugin/plugin.json
    │   └── skills/enter-fixture-result/
    │       ├── SKILL.md
    │       └── agents/openai.yaml
    └── veo-match-analytics/
        ├── .codex-plugin/plugin.json
        └── skills/veo-match-analytics/
            ├── SKILL.md
            ├── agents/openai.yaml
            └── references/
```

The marketplace manifest is in `.agents/plugins/marketplace.json`; plugin source is kept under `plugins/`.

## Development

After changing the skill or its references, validate both the skill and plugin from the repository root:

```sh
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/<plugin-name>/skills/<skill-name>

python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugins/<plugin-name>
```

Before distributing an updated local build, refresh its cache-buster rather than incrementing the semantic version solely to force reinstallation:

```sh
python3 ~/.codex/skills/.system/plugin-creator/scripts/update_plugin_cachebuster.py \
  plugins/<plugin-name>
```

Validate again, commit the source change and generated version change together, then refresh and reinstall the marketplace plugin in a new Codex task.

## Documentation

See the [official OpenAI plugin packaging documentation](https://developers.openai.com/plugins/build/plugins) for marketplace, installation, and plugin-structure details.
