---
name: analyticom-player-photo
description: Download an original Analyticom player photo using the saved ClubATX player-to-athlete link. Use when asked to download a linked athlete's player picture. Requires an exact athlete slug and local download directory; does not change athlete records or generate headshots.
---

# Linked player photo

Use `download_linked_player_photo` with the exact `athlete_slug` and an absolute `output_directory` in the user's workspace (default: `downloads/analyticom-player-photos` under the current workspace). Create the concrete absolute path from the current workspace context.

If the user supplies a name, resolve the exact athlete through available authorized ClubATX tools first. Ask which athlete only when the record remains ambiguous or no lookup is available. Never infer a player link from a matching name, jersey number, fixture analytics source_player_id, or team.

The tool reads `athletes` and `analyticom_player_links`, follows the saved `person_id`, fetches the profile and its exact `picture`, and saves the original PNG, JPEG, GIF or WebP bytes. Organization 168094 is the verified BC Soccer default; use another organization only from user or verified project context.

Do not construct public photo URLs, follow pictureLink URLs, reconstruct hidden profiles, change player links, upload images, or replace `athletes.photo_url` as part of this workflow. A missing link must be created using the existing ClubATX admin linking flow before downloading. A hidden profile or missing picture means the photo is unavailable.

If credentials are missing, direct the user to configure the local environment as described in the plugin README. Never request or include credentials in chat or tool arguments. Existing output files are preserved: use a different directory if another download is needed.

After success, provide a clickable local file link and show the photo with an absolute-path Markdown image. Include the athlete and linked person ID. Report a download only when the tool returns a saved path. Do not claim that the athlete profile photo was updated.
