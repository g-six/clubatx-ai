---
name: futty-card-style
description: Generate a reusable futty football player card style from a ClubATX organization or team crest and the user's design directions. Use for crest-based card templates, materials, borders, palette, and decorative variants. Also use to check the connected card generation tool without generating an image.
---

# ClubAtx Futty Cards

Use the connected ClubATX MCP tool `generate_futty_card_style`. The server is
`https://api.clubathletix.com/mcp`; its OAuth connection requires a ClubATX
administrator for generation. Use the host's normal connection and passkey
sign-in flow. Do not ask for, read, extract, print, or package provider secrets,
bearer tokens, browser cookies, or database credentials.

## Check availability

Inspect the connected tool list and the current tool schema. The source-backed
contract below is a baseline; use the live schema when available. If the tool
is missing, refresh or reconnect this plugin and explain that the API feature
must be deployed. Do not claim generation is available just because public
endpoint metadata is healthy. Do not call a mutating tool to test sign-in.
If the user only asks to check the connection, stop after discovery and report
whether the exact card-generation tool is available.

## Choose the crest and request

Supply a nonblank `request` of at most 2000 characters containing the user's
aesthetic directions, plus exactly one source:

- `team_name`: the exact saved ClubATX team name, 1–160 characters. The server
  uses its current crest, falling back to the organization crest when the team
  has none. Do not guess a team name or invent a team ID.
- `organization_id`: the exact saved organization UUID, using its current crest.
- `crest_url`: a direct HTTPS PNG, JPEG, or WebP URL from the deployment's
  configured Vercel Blob store, up to 5 MB, without query parameters or a fragment.
  Arbitrary websites, local paths, and attached images are not accepted directly.

Reuse a source already identified by the user or verified in context. If it is
missing or ambiguous, ask only for the source information needed to identify it.
If aesthetic directions are missing, use a premium template in the crest's
colours with a detailed border, unless the user has expressed another preference.
For an attachment or unsupported URL, explain the stored-crest requirement; use
an available authorized upload workflow only when the user has requested upload.
Do not invent an upload tool or modify saved team/organization crests.

## Generate the template

An explicit request to generate authorizes one generation; do not add a separate
confirmation step. Before calling, briefly explain that it creates a new PNG
using paid image generation. Do not generate a batch, automatically retry, or
create additional variants unless the user requests them.

Example arguments (only submit for a team actually selected by the user):

```json
{
  "team_name": "Salsal FC",
  "request": "Use the crest colours with a metallic border and subtle geometric textures."
}
```

Call `generate_futty_card_style` and allow up to 300 seconds. It creates a portrait
card style template with a crest-derived palette and recognizable badge, blank
areas for the player portrait, name, rating, position, and six statistics, and a
transparent exterior. It does not generate a completed player card or write
athlete, organization, or team records. The original crest is preserved.

## Report the result

Only say the PNG was saved after a successful tool response containing `data.url`
in `structuredContent` or parsed text content. Return the exact generated URL.
For public output, display the returned image when the host supports it and
include a download link. For `access: private`, explain that the URL requires
authenticated Blob access; do not present it as a public preview or make it public.

Recommend checking the card layout, transparency, and crest lettering/symbols
before adoption. Do not promise exact crest pixels, fixed layout coordinates,
transparent pixels, or successful visual QA without inspecting the generated image.

If the tool returns `isError`, report the failure rather than fabricating a URL.
On timeout or a lost response, say the outcome is unconfirmed and do not retry:
the request may already have incurred costs or saved a PNG. A further attempt
requires a new user request. Respect administrator-only errors and missing-crest
errors. Do not switch to another tool or provider to bypass these requirements.
The shared MCP may advertise fixture tools; do not invoke those for card requests.
