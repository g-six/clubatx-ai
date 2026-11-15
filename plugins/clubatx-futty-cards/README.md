# ClubAtx Futty Cards

Generate reusable football player card style PNGs from team and organization
crests through the existing OAuth-protected ClubATX MCP endpoint.

## Install from this checkout

From the ClubAtx AI repository:

```sh
codex plugin marketplace add .
codex plugin add clubatx-futty-cards@clubatx-ai
```

The marketplace may already be registered. Start a new Codex chat after installation,
select **ClubAtx Futty Cards**, and connect its MCP server using your ClubATX
administrator account and the normal passkey sign-in flow.

After these files are committed and pushed to the GitHub marketplace, other machines
can install with:

```sh
codex plugin marketplace add g-six/clubatx-ai --ref main
codex plugin add clubatx-futty-cards@clubatx-ai
```

No Node server, API keys, OpenAI setup, or Supabase credentials are required on
the plugin client. Those remain on the existing API deployment.

## Verify discovery without generating

Ask:

> Check that generate_futty_card_style is available. Do not generate an image.

Confirm that the exact tool appears in the authenticated tool list. If it is absent,
refresh/reconnect after deploying the futty card API feature. Public MCP readiness
alone does not prove the tool is deployed. This package does not deploy API code.

## Generate a real card style

Ask, substituting an exact saved team name:

> Generate one futty card style for Salsal FC using its saved crest. Use the crest
> colours, a metallic border, and subtle geometric textures. Leave player and
> statistics areas blank.

Equivalent tool arguments:

```json
{
  "team_name": "Salsal FC",
  "request": "Use the crest colours with a metallic border and subtle geometric textures."
}
```

Use exactly one of `team_name`, `organization_id`, or `crest_url`. Organization IDs
are UUIDs; team names are exact saved names. Direct crest URLs must belong to the
API's configured Blob store, have no query/fragment, and reference PNG/JPEG/WebP
files up to 5 MB. The request accepts up to 2000 characters. A team without its own
crest uses its organization's crest.

Each execution uses paid generation and saves a new PNG; allow up to 300 seconds.
Successful results include `data.url`, `pathname`, `access`, and the source crest.
Private output requires authenticated Blob access. Original crests and saved team,
organization, and athlete records are preserved. Do not automatically retry a
timeout or lost response because a previous request may have completed.

Review crest fidelity, card layout, and transparency before adopting the template.
The output has blank areas for player details; it is not a completed athlete card.

## Connection and source layout

- Remote MCP: `https://api.clubathletix.com/mcp/futty-cards`, Streamable HTTP.
  This dedicated alias keeps Futty Cards tool discovery independent from the
  shared commentary connection while using the same authenticated handler.
- Authentication: existing OAuth discovery, dynamic client registration, PKCE,
  and ClubATX passkey sign-in; generation is administrator-only.
- The server currently advertises `fixtures:read fixtures:write events:write` as
  its OAuth scope set. This plugin preserves that existing flow; it introduces
  no new scopes. The shared server can advertise fixture tools as well as card
  generation; the bundled skill uses only card generation for this workflow.
- `plugin.json` and `mcp.json`: portable Agent Plugins 1.0 package.
- `.codex-plugin/plugin.json` and `.mcp.json`: Codex marketplace compatibility,
  with a 300-second tool timeout.
- `skills/futty-card-style/`: crest-based generation and read-only discovery workflow.

Public endpoint metadata and OAuth configuration were verified during authoring.
Authenticated tool discovery and live image generation were not run; those require
an authorized connection. The tool contract was checked against the API source.
