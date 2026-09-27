---
name: enter-fixture-result
description: Securely enter or replace a completed Summer Progressive League fixture scoresheet, including half length, goals, assists, cards, recipients, and event minutes. Use when asked to record, correct, preview, or submit a fixture result from the ClubATX workspace.
---

# Enter Fixture Result

Use the OAuth-protected fixture-result MCP tools when they are available. This is the preferred path on ChatGPT web, including a phone browser, and in remote sessions because it does not need Computer Use, a local checkout, or a client secret. Custom MCP apps are not currently available in the native ChatGPT mobile app. On the configured Mac host, the Keychain-backed `npm run fixture:result:secure` command remains the fallback. Never provide the skill with `SUPABASE_SERVICE_ROLE_KEY`.

## Transport Selection

1. If `find_fixtures`, `search_athletes`, `preview_fixture_scoresheet`, and `save_fixture_scoresheet` are available, use the Mobile / Remote Workflow below. Do not use Computer Use or run the local CLI.
2. Otherwise, if the clubatx repository and configured Keychain are available, use the Local Workflow.
3. If neither transport is available, ask the user to connect the deployed MCP endpoint documented in `docs/fixture-result-mobile.md`. Do not ask them to paste an API client secret into the conversation.

## Authentication

The remote MCP transport uses OAuth 2.1 authorization code with PKCE. The user signs in with an allowed staff Google account, grants the fixture read/write scopes, and the client stores short-lived access and rotating refresh tokens. Never print or repeat OAuth codes, access tokens, refresh tokens, or scoresheet confirmation tokens.

The local command requires these values in the process environment:

- `FIXTURE_RESULT_API_URL`: deployed clubatx origin, such as `https://league.example.com`
- `FIXTURE_RESULT_CLIENT_ID`: revocable `frc_...` API client identifier
- `FIXTURE_RESULT_CLIENT_SECRET`: high-entropy secret paired with that client

On the configured Mac host, use the Keychain-backed command:

```bash
npm run fixture:result:secure
```

For other hosts, prefer a secret manager that injects values only for the command. With 1Password CLI, keep an ignored env file containing only secret references and use `op run --env-file=.env.fixture-result -- npm run fixture:result`.

Do not put the resolved secret in repository files, skill files, prompts, command arguments, shell history, or logs. Do not print environment values while diagnosing authentication. Ask the user to inject or rotate credentials when they are absent or rejected.

The client exchanges its credentials over HTTPS for a scoped bearer token that expires in five minutes. The database service-role key remains exclusively in the deployed server environment.

## Mobile / Remote Workflow

1. Call `find_fixtures` with the local kickoff date and time, then identify the exact fixture from the returned teams.
2. Read back any existing events. If events exist and append-versus-replace intent is unclear, ask the user before continuing.
3. Collect the half duration and every event. For each event collect the team, event type, recipient role, player name when applicable, and optional minute/added time. Call `search_athletes` for each distinct player name; let the user choose a matching athlete or explicitly leave the name unlinked. Reuse that choice for repeated events by the same player.
4. Call `preview_fixture_scoresheet` with `mode` set to `append` or `replace`. Report the calculated final score, half length, and event count. Do not expose the returned `confirmation_token`.
5. Call `save_fixture_scoresheet` with the exact same inputs and returned confirmation token only after the user explicitly authorizes that write. If the token expires or the current scoresheet changes, preview again and request confirmation for the new preview.
6. Report the saved fixture and final score.

## Local Workflow

1. Confirm the current directory is the clubatx repository.
2. Ensure the three required variables are injected without revealing their values.
3. For a preview on the configured Mac host, run `npm run fixture:result:secure -- --dry-run` and complete the prompts.
4. When entering a player event, review the possible athlete matches and select the existing athlete when confirmed. Leave the event unlinked when none of the candidates is the same person.
5. For a requested database update, run `npm run fixture:result:secure`, select the kickoff and fixture, enter the half duration and events, review the calculated score, and submit only after the user has authorized the write.
6. Report the fixture and final score without exposing credentials or tokens.

When a fixture already has events, choose append or replace according to the user's request. If that intent is unclear, preview the current events and ask before replacing them.

## Client Administration

Client creation, rotation, and revocation are administrator-only operations because the management command uses the server-side Supabase service role:

```bash
npm run fixture:client -- create "Codex fixture result skill"
npm run fixture:client -- rotate frc_client_id
npm run fixture:client -- revoke frc_client_id
```

Store a newly printed secret immediately; only its keyed HMAC is persisted, so it cannot be recovered later. Keep `FIXTURE_RESULT_CLIENT_SECRET_PEPPER` and `FIXTURE_RESULT_API_JWT_SECRET` as separate random values of at least 32 bytes in the deployment secret manager. Apply edge rate limiting to `/api/fixture-results/token` and permit the fixture-result routes only over HTTPS.

OAuth clients register dynamically as public clients and must use an exact HTTPS redirect URI (loopback HTTP is development-only), PKCE S256, and the MCP resource indicator. Staff access remains restricted to the portal's allowed Google domain. Apply edge rate limiting to the OAuth registration, authorization, token, and MCP routes.
