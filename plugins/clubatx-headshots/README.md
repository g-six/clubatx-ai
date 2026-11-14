# ClubAtx Headshots plugin

Site ID: `appgprj_6af881f4d46c8191ba36d59d029110f9`

Exposes `create_headshot` and `headshot_connection_status` through `/mcp`.
Wraps only `POST https://api.clubathletix.com/v1/images/headshot`.

Configure `CLUBATX_API_KEY` as a private Sites runtime secret using a ClubAtx
`read_write` key. Never put the key in source or tool arguments.

The source was checked against `public/openapi.json` and the endpoint implementation.
Live OpenAPI retrieval and Git publication were blocked by DNS in the execution environment.
The Site is registered but has not been published, so its plugin is not yet provisioned.
Resume publication using the existing Site ID; do not create another Site.
Follow the Sites source workflow, get a fresh write credential, build with
`bash scripts/build.sh`, validate with `node scripts/validate-artifact.mjs`,
then publish the matching pushed source archive.

Profile photo replacement occurs only with `athlete_slug`. Generation is not
idempotent; never automatically retry an uncertain request. Preserve generated
PNG metadata on 409/500 and report the profile update state accurately.
