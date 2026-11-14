# Analyticom Player Photo

Local Codex plugin with one tool, `download_linked_player_photo`. Requires Node.js 22+ on `PATH`. No dependency installation is needed.

The tool follows the existing `public.analyticom_player_links.athlete_slug → person_id` mapping, checks that the athlete exists, reads the Analyticom profile, and downloads its exact `picture`. It accepts the JSON/base64 image envelope or direct image bytes. It verifies the file signature, limits photos to 5 MiB, rechecks the link before saving, and returns an absolute path, byte count and SHA-256 digest. Existing files are never overwritten. Database operations are GET requests only; `athletes.photo_url` is not changed.

## Configure and install

Provide these variables to the local MCP process, or set `CLUBATX_PHOTO_ENV_FILE` to the absolute path of a private environment file containing them:

| Variable | Purpose |
| --- | --- |
| `SUPABASE_URL` | ClubATX Supabase project URL (`NEXT_PUBLIC_SUPABASE_URL` also supported) |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only credential to read athletes and the protected player-link table |
| `REST_API_KEY` | Analyticom API credential |
| `REST_API_BASE_URL` | Optional; defaults to `https://api-latam.analyticom.de/api/live/CSA_BCS/` |
| `ANALYTICOM_ORGANIZATION_ID` | Optional; defaults to the existing BC Soccer organization `168094` |

Use a private local environment file outside this plugin directory. Do not paste credentials into chat, commit them, package them, or add them to tool arguments. The optional environment file is loaded by Node without executing shell code. The server uses no browser or public image proxy. Supabase service-role access is local and privileged; this is a single-user operator tool, not a remotely hosted multi-user service. The existing player-link table restricts reads to service_role; no grants or RLS changes are needed.

From the configured ClubATX marketplace:

```sh
codex plugin add analyticom-player-photo@clubatx-ai
```

Open a new Codex chat after installation to load the tool. The compatibility config resolves its command relative to the plugin root; the portable `mcp.json` uses `${PLUGIN_ROOT}`.

Example prompt: “Download the Analyticom player photo for athlete `exact-athlete-slug`.”

Example arguments (replace placeholders with an actual slug and absolute local path):

```json
{
  "athlete_slug": "exact-athlete-slug",
  "output_directory": "/absolute/workspace/downloads/analyticom-player-photos"
}
```

Missing or ambiguous links, hidden profiles (`hideProfile`), mismatched person IDs, absent pictures, redirects, upstream errors, invalid image bytes, and oversized images fail without creating a photo. A successful result includes the original image file; updating the ClubATX profile photo is a separate action.

## Verify

```sh
node --test plugins/analyticom-player-photo/tests/photo.test.mjs
```

Source schema was verified against the ClubATX API's `20261004154153_add_analyticom_player_links.sql` migration and admin player-link route. Analyticom requests follow the existing REST API Client's player and image endpoints and BC Soccer headers.
