# REST API Client

This Codex plugin exposes one MCP tool, `submit_request`, for sending authenticated requests to a configured REST API.

## Configuration

Set the API key before starting Codex:

```sh
export REST_API_KEY="replace-with-your-api-key"
```

The server adds `API_KEY: <REST_API_KEY>` to every request. Do not put the key in prompts, tool arguments, or plugin files.

Requests reproduce the BC Soccer client headers required by the API:

```http
Host: api-latam.analyticom.de
Accept: */*
Connection: keep-alive
User-Agent: BC%20Soccer/8 CFNetwork/3896.100.1.2.1 Darwin/27.0.0
Accept-Language: en
API_KEY: <REST_API_KEY>
Cookie: SRVNAME=d21
```

The default API base URL is `https://api-latam.analyticom.de/api/live/CSA_BCS/`. Set `REST_API_BASE_URL` only when you need to override it.

Requests cannot switch to another origin or escape the configured base path, redirects are returned without being followed, and response bodies are limited to 1 MiB.

## Player information

`get_player` calls:

```text
GET /player/{player_id}
    ?organizationIdFilter={organization_id_filter}
```

Example arguments:

```json
{
  "player_id": 8408855,
  "organization_id_filter": 168094
}
```

The endpoint returns the player information available to the configured organization. Protected or hidden profile fields must be treated as unavailable rather than inferred.

## Player pictures

`get_player_picture` uses the `picture` value from a `get_player` response and calls:

```text
GET /images/{picture}
    ?organizationIdFilter={organization_id_filter}
```

Example arguments:

```json
{
  "picture": "63efcb80-fc51-4d50-b9d9-9be68fee4d72",
  "organization_id_filter": 168094
}
```

The tool reads the authenticated binary response and returns it as MCP image content. JPEG, PNG, GIF, and WebP signatures are recognized if the API does not provide a specific image content type. Image responses are limited to 5 MiB.

## List soccer matches

`list_soccer_matches` calls:

```text
GET /competition/{competition_id}/matches/paginated/past/-7
    ?organizationIdFilter={organization_id_filter}
    &page={page}
    &pageSize={page_size}
```

Example arguments:

```json
{
  "competition_id": 400185941,
  "organization_id_filter": 168094,
  "page": 1,
  "page_size": 10
}
```

The endpoint returns a paginated object containing `result` match records and the total `size`.

## Competition goal statistics

`get_competition_goal_stats` calls:

```text
GET /competition/{competition_id}/stats/goals
    ?organizationIdFilter={organization_id_filter}
```

Example arguments:

```json
{
  "competition_id": 400185941,
  "organization_id_filter": 168094
}
```

The response body is a ranked array. Each row contains a `player`, numeric goal count in `value`, and the player's `team`. Some protected player profiles are returned as `N/A` with `hideProfile: true`.

## Competition yellow-card statistics

`get_competition_yellow_card_stats` calls:

```text
GET /competition/{competition_id}/stats/yellowCards
    ?organizationIdFilter={organization_id_filter}
```

It accepts the same `competition_id` and `organization_id_filter` arguments as goal statistics. The response is a ranked array of `player`, yellow-card count in `value`, and `team`.

## Competition red-card statistics

`get_competition_red_card_stats` calls:

```text
GET /competition/{competition_id}/stats/redCards
    ?organizationIdFilter={organization_id_filter}
```

It accepts the same competition and organization arguments. The response is a ranked array of `player`, red-card count in `value`, and `team`.

## Match lineups

`get_match_lineups` calls:

```text
GET /match/{match_id}/lineups
    ?organizationIdFilter={organization_id_filter}
```

Example arguments:

```json
{
  "match_id": 400204631,
  "organization_id_filter": 168094
}
```

The response body contains `home` and `away`. Each side contains player and official arrays. Player fields identify starters, substitutes, captains, shirt numbers, optional positions and formation positions, protected profiles, and any embedded match events returned by the endpoint.

## Project agent usage

The bundled `soccer-match-feed` skill teaches an agent in a project to call the player, player-picture, match-list, lineup, goal-statistics, yellow-card-statistics, and red-card-statistics tools; interpret their distinct meanings; handle binary player images, pagination, team sides, starters, substitutes, postponed matches, and protected profiles correctly; and use those records directly in its analysis context. The API key remains in the MCP server environment and is never included in the agent prompt.

Enable this plugin for the project, start a new task so the skill and MCP tool load, then ask the agent to list, summarize, filter, or analyze matches. Provide the competition and organization IDs when they are not already present in project context.

## Supported requests

The generic `submit_request` tool supports `GET`, `POST`, `PUT`, `PATCH`, and `DELETE`, optional query parameters, and optional JSON request bodies. Generic requests require approval; the dedicated read-only match-list tool is pre-approved.

## Local smoke test

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke-test","version":"1.0.0"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | ./scripts/start-mcp.sh
```
