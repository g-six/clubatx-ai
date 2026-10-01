---
name: soccer-match-feed
description: Load Analyticom soccer matches, goal statistics, and yellow- or red-card statistics into an agent's context for listing, filtering, summarization, or analysis. Use when a project task asks about matches, scorers, goal leaders, or discipline for a known competition and organization; do not use for entering or changing results.
---

# Soccer Match Feed

Use `list_soccer_matches` for match schedules and results. Use `get_competition_goal_stats` for scorers, goal leaders, or player goal totals. Use `get_competition_yellow_card_stats` for cautions or player yellow-card totals. Use `get_competition_red_card_stats` for dismissals or player red-card totals. All are read-only GET requests whose credential remains inside the MCP server.

Require positive integer `competition_id` and `organization_id_filter` values. Reuse IDs already supplied in the conversation or project context. Ask for a missing ID instead of guessing it. Default to page 1 and page size 10 unless the user requests another range.

Read match records from `response.body.result` and the total available count from `response.body.size`. Treat `size` as the total result count, not the current page length. Fetch additional pages only when the user asks for all matches or the requested analysis requires them.

Read goal-stat rows from the array in `response.body`. Each row contains `player`, numeric goal count `value`, and `team`. Preserve `personId` and `team.id` when identity matters. When `player.hideProfile` is true or its name is `N/A`, report it as an undisclosed player for that team; do not infer an identity.

Read yellow-card rows from the array in `response.body`. They use the same structure as goal statistics, but `value` means accumulated yellow cards. Label it explicitly as yellow cards and never combine it numerically with goal values.

Read red-card rows from the array in `response.body`. They use the same structure, but `value` means accumulated red cards. Keep red- and yellow-card totals separate; do not infer suspensions or disciplinary sanctions from card totals alone.

Call multiple tools only when the requested analysis actually combines match outcomes, scoring, or discipline. Do not claim that a goal-stat, yellow-card, or red-card row belongs to a particular match because these endpoints report competition aggregates.

Preserve source IDs and statuses in factual output. A postponed match can omit score objects; do not treat missing scores as zero. `dateTimeUTC` is Unix epoch milliseconds. Convert it to the user's requested timezone when presenting dates, and state the timezone.

Feed the returned records directly into the invoking agent's reasoning context. Summarize or analyze them according to the project request, but do not persist them, message another agent, or modify league data unless the user separately requests and authorizes that action.

Never request, display, or place `REST_API_KEY` in prompts or tool arguments. If the tool returns an authentication error, report it without exposing request secrets.
