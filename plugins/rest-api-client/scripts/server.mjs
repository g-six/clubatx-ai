#!/usr/bin/env node

import process from "node:process";
import readline from "node:readline";
import { Buffer } from "node:buffer";

const SERVER_NAME = "rest-api-client";
const SERVER_VERSION = "0.1.0";
const DEFAULT_BASE_URL = "https://api-latam.analyticom.de/api/live/CSA_BCS/";
const MAX_RESPONSE_BYTES = 1024 * 1024;
const MAX_IMAGE_RESPONSE_BYTES = 5 * 1024 * 1024;
const DEFAULT_TIMEOUT_MS = 30_000;
const ALLOWED_METHODS = new Set(["GET", "POST", "PUT", "PATCH", "DELETE"]);

function success(id, result) {
  return { jsonrpc: "2.0", id, result };
}

function failure(id, code, message, data) {
  const error = { code, message };
  if (data !== undefined) error.data = data;
  return { jsonrpc: "2.0", id: id ?? null, error };
}

function write(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

function toolError(message) {
  return {
    content: [{ type: "text", text: message }],
    isError: true,
  };
}

function getConfiguration() {
  const rawBaseUrl = process.env.REST_API_BASE_URL || DEFAULT_BASE_URL;
  const apiKey = process.env.REST_API_KEY;

  if (!apiKey) throw new Error("REST_API_KEY is not configured.");

  let baseUrl;
  try {
    baseUrl = new URL(rawBaseUrl);
  } catch {
    throw new Error("REST_API_BASE_URL must be a valid absolute URL.");
  }

  if (!new Set(["http:", "https:"]).has(baseUrl.protocol)) {
    throw new Error("REST_API_BASE_URL must use HTTP or HTTPS.");
  }
  if (baseUrl.username || baseUrl.password) {
    throw new Error("REST_API_BASE_URL must not contain credentials.");
  }

  return { baseUrl, apiKey };
}

function buildUrl(baseUrl, path, query) {
  if (typeof path !== "string" || !path.startsWith("/")) {
    throw new Error("path must be a string beginning with '/'.");
  }
  if (path.startsWith("//") || path.includes("\\")) {
    throw new Error("path must be a relative API path on the configured origin.");
  }

  const base = new URL(baseUrl.href);
  if (!base.pathname.endsWith("/")) base.pathname += "/";
  const url = new URL(path.replace(/^\/+/, ""), base);
  if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname)) {
    throw new Error("The request URL must stay beneath the configured API base URL.");
  }
  if (url.hash) throw new Error("path must not contain a URL fragment.");

  if (query !== undefined) {
    if (!query || typeof query !== "object" || Array.isArray(query)) {
      throw new Error("query must be an object when provided.");
    }
    for (const [name, value] of Object.entries(query)) {
      if (value === null || value === undefined) continue;
      const values = Array.isArray(value) ? value : [value];
      for (const item of values) {
        if (!["string", "number", "boolean"].includes(typeof item)) {
          throw new Error(`query.${name} must contain only strings, numbers, or booleans.`);
        }
        url.searchParams.append(name, String(item));
      }
    }
  }

  return url;
}

async function readLimitedBytes(response, maximumBytes = MAX_RESPONSE_BYTES) {
  if (!response.body) return new Uint8Array();

  const reader = response.body.getReader();
  const chunks = [];
  let total = 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > maximumBytes) {
      await reader.cancel();
      throw new Error(`Response exceeded the ${maximumBytes}-byte limit.`);
    }
    chunks.push(value);
  }

  const combined = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    combined.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return combined;
}

async function readLimitedBody(response) {
  return new TextDecoder().decode(await readLimitedBytes(response));
}

function detectImageMimeType(bytes, contentType) {
  const normalizedContentType = contentType.split(";", 1)[0].trim().toLowerCase();
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
    return "image/jpeg";
  }
  if (
    bytes.length >= 8
    && bytes[0] === 0x89
    && bytes[1] === 0x50
    && bytes[2] === 0x4e
    && bytes[3] === 0x47
    && bytes[4] === 0x0d
    && bytes[5] === 0x0a
    && bytes[6] === 0x1a
    && bytes[7] === 0x0a
  ) {
    return "image/png";
  }

  const signature = new TextDecoder("ascii").decode(bytes.subarray(0, 12));
  if (signature.startsWith("GIF87a") || signature.startsWith("GIF89a")) return "image/gif";
  if (signature.startsWith("RIFF") && signature.slice(8, 12) === "WEBP") return "image/webp";
  if (normalizedContentType.startsWith("image/")) return normalizedContentType;
  return null;
}

async function performRequest({ method, path, query, body }) {
  const { baseUrl, apiKey } = getConfiguration();
  method = String(method ?? "GET").toUpperCase();
  if (!ALLOWED_METHODS.has(method)) {
    throw new Error(`method must be one of: ${[...ALLOWED_METHODS].join(", ")}.`);
  }

  const url = buildUrl(baseUrl, path, query);
  const headers = {
    Host: url.host,
    Accept: "*/*",
    Connection: "keep-alive",
    "User-Agent": "BC%20Soccer/8 CFNetwork/3896.100.1.2.1 Darwin/27.0.0",
    "Accept-Language": "en",
    API_KEY: apiKey,
    Cookie: "SRVNAME=d21",
  };

  const options = {
    method,
    headers,
    redirect: "manual",
    signal: AbortSignal.timeout(DEFAULT_TIMEOUT_MS),
  };

  if (body !== undefined) {
    if (method === "GET") throw new Error("GET requests cannot include a body.");
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);
  const bodyText = await readLimitedBody(response);
  const contentType = response.headers.get("content-type") ?? "";
  let responseBody = bodyText;
  if (contentType.includes("application/json") && bodyText) {
    try {
      responseBody = JSON.parse(bodyText);
    } catch {
      // Preserve malformed JSON as text so the caller can inspect the API response.
    }
  }

  const result = {
    request: { method, url: url.href },
    response: {
      status: response.status,
      statusText: response.statusText,
      contentType: contentType || null,
      body: responseBody,
    },
  };

  return {
    content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    isError: !response.ok,
  };
}

async function submitRequest(args) {
  return performRequest({
    method: args?.method,
    path: args?.path,
    query: args?.query,
    body: args?.body,
  });
}

async function listSoccerMatches(args) {
  const competitionId = args?.competition_id;
  const organizationId = args?.organization_id_filter;
  const page = args?.page ?? 1;
  const pageSize = args?.page_size ?? 10;

  for (const [name, value] of Object.entries({
    competition_id: competitionId,
    organization_id_filter: organizationId,
    page,
    page_size: pageSize,
  })) {
    if (!Number.isSafeInteger(value) || value <= 0) {
      throw new Error(`${name} must be a positive integer.`);
    }
  }
  if (pageSize > 100) throw new Error("page_size must be at most 100.");

  return performRequest({
    method: "GET",
    path: `/competition/${competitionId}/matches/paginated/past/-7`,
    query: {
      organizationIdFilter: organizationId,
      page,
      pageSize,
    },
  });
}

async function listFutureSoccerMatches(args) {
  const competitionId = args?.competition_id;
  const organizationId = args?.organization_id_filter;
  const page = args?.page ?? 1;
  const pageSize = args?.page_size ?? 10;

  for (const [name, value] of Object.entries({
    competition_id: competitionId,
    organization_id_filter: organizationId,
    page,
    page_size: pageSize,
  })) {
    if (!Number.isSafeInteger(value) || value <= 0) {
      throw new Error(`${name} must be a positive integer.`);
    }
  }
  if (pageSize > 100) throw new Error("page_size must be at most 100.");

  return performRequest({
    method: "GET",
    path: `/competition/${competitionId}/matches/paginated/future/7`,
    query: {
      organizationIdFilter: organizationId,
      page,
      pageSize,
    },
  });
}

async function getCompetitionGoalStats(args) {
  const competitionId = args?.competition_id;
  const organizationId = args?.organization_id_filter;

  for (const [name, value] of Object.entries({
    competition_id: competitionId,
    organization_id_filter: organizationId,
  })) {
    if (!Number.isSafeInteger(value) || value <= 0) {
      throw new Error(`${name} must be a positive integer.`);
    }
  }

  return performRequest({
    method: "GET",
    path: `/competition/${competitionId}/stats/goals`,
    query: { organizationIdFilter: organizationId },
  });
}

async function getCompetitionYellowCardStats(args) {
  const competitionId = args?.competition_id;
  const organizationId = args?.organization_id_filter;

  for (const [name, value] of Object.entries({
    competition_id: competitionId,
    organization_id_filter: organizationId,
  })) {
    if (!Number.isSafeInteger(value) || value <= 0) {
      throw new Error(`${name} must be a positive integer.`);
    }
  }

  return performRequest({
    method: "GET",
    path: `/competition/${competitionId}/stats/yellowCards`,
    query: { organizationIdFilter: organizationId },
  });
}

async function getCompetitionRedCardStats(args) {
  const competitionId = args?.competition_id;
  const organizationId = args?.organization_id_filter;

  for (const [name, value] of Object.entries({
    competition_id: competitionId,
    organization_id_filter: organizationId,
  })) {
    if (!Number.isSafeInteger(value) || value <= 0) {
      throw new Error(`${name} must be a positive integer.`);
    }
  }

  return performRequest({
    method: "GET",
    path: `/competition/${competitionId}/stats/redCards`,
    query: { organizationIdFilter: organizationId },
  });
}

async function getMatchLineups(args) {
  const matchId = args?.match_id;
  const organizationId = args?.organization_id_filter;

  for (const [name, value] of Object.entries({
    match_id: matchId,
    organization_id_filter: organizationId,
  })) {
    if (!Number.isSafeInteger(value) || value <= 0) {
      throw new Error(`${name} must be a positive integer.`);
    }
  }

  return performRequest({
    method: "GET",
    path: `/match/${matchId}/lineups`,
    query: { organizationIdFilter: organizationId },
  });
}

async function getPlayer(args) {
  const playerId = args?.player_id;
  const organizationId = args?.organization_id_filter;

  for (const [name, value] of Object.entries({
    player_id: playerId,
    organization_id_filter: organizationId,
  })) {
    if (!Number.isSafeInteger(value) || value <= 0) {
      throw new Error(`${name} must be a positive integer.`);
    }
  }

  return performRequest({
    method: "GET",
    path: `/player/${playerId}`,
    query: { organizationIdFilter: organizationId },
  });
}

async function getPlayerPicture(args) {
  const picture = args?.picture;
  const organizationId = args?.organization_id_filter;

  if (typeof picture !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(picture)) {
    throw new Error("picture must be a non-empty image identifier containing only letters, numbers, dots, underscores, or hyphens.");
  }
  if (!Number.isSafeInteger(organizationId) || organizationId <= 0) {
    throw new Error("organization_id_filter must be a positive integer.");
  }

  const { baseUrl, apiKey } = getConfiguration();
  const url = buildUrl(baseUrl, `/images/${encodeURIComponent(picture)}`, {
    organizationIdFilter: organizationId,
  });
  const response = await fetch(url, {
    method: "GET",
    headers: {
      Host: url.host,
      Accept: "*/*",
      Connection: "keep-alive",
      "User-Agent": "BC%20Soccer/8 CFNetwork/3896.100.1.2.1 Darwin/27.0.0",
      "Accept-Language": "en",
      API_KEY: apiKey,
      Cookie: "SRVNAME=d21",
    },
    redirect: "manual",
    signal: AbortSignal.timeout(DEFAULT_TIMEOUT_MS),
  });
  const bytes = await readLimitedBytes(response, MAX_IMAGE_RESPONSE_BYTES);
  const responseContentType = response.headers.get("content-type") ?? "";
  const metadata = {
    request: { method: "GET", url: url.href },
    response: {
      status: response.status,
      statusText: response.statusText,
      contentType: responseContentType || null,
      byteLength: bytes.byteLength,
    },
  };

  if (!response.ok) {
    return {
      content: [{
        type: "text",
        text: `${JSON.stringify(metadata, null, 2)}\n\n${new TextDecoder().decode(bytes)}`,
      }],
      isError: true,
    };
  }

  let imageBytes = bytes;
  let declaredImageType = responseContentType;
  if (responseContentType.toLowerCase().includes("application/json")) {
    let imageEnvelope;
    try {
      imageEnvelope = JSON.parse(new TextDecoder().decode(bytes));
    } catch {
      return toolError("The image endpoint returned malformed JSON.");
    }

    if (
      !imageEnvelope
      || typeof imageEnvelope !== "object"
      || typeof imageEnvelope.value !== "string"
      || typeof imageEnvelope.contentType !== "string"
    ) {
      return toolError("The image endpoint response did not contain contentType and base64 value fields.");
    }

    declaredImageType = imageEnvelope.contentType;
    imageBytes = Buffer.from(imageEnvelope.value.replace(/\s/g, ""), "base64");
    metadata.response.pictureLink = typeof imageEnvelope.pictureLink === "string"
      ? imageEnvelope.pictureLink
      : null;
    metadata.response.imageContentType = declaredImageType;
    metadata.response.imageByteLength = imageBytes.byteLength;
  }

  const mimeType = detectImageMimeType(imageBytes, declaredImageType);
  if (!mimeType) {
    return toolError(`The image endpoint returned unsupported image content type: ${declaredImageType || "unknown"}.`);
  }

  return {
    content: [
      { type: "text", text: JSON.stringify(metadata, null, 2) },
      { type: "image", data: Buffer.from(imageBytes).toString("base64"), mimeType },
    ],
    isError: false,
  };
}

const tools = [
  {
    name: "get_player_picture",
    description:
      "Get an Analyticom player picture using the picture identifier returned by get_player.",
    inputSchema: {
      type: "object",
      additionalProperties: false,
      properties: {
        picture: {
          type: "string",
          minLength: 1,
          maxLength: 128,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._-]*$",
          description: "Picture identifier from the player's picture field, for example 63efcb80-fc51-4d50-b9d9-9be68fee4d72.",
        },
        organization_id_filter: {
          type: "integer",
          minimum: 1,
          description: "Analyticom organization ID used by organizationIdFilter, for example 168094.",
        },
      },
      required: ["picture", "organization_id_filter"],
    },
  },
  {
    name: "get_player",
    description:
      "Get Analyticom player information for one player ID and organization.",
    inputSchema: {
      type: "object",
      additionalProperties: false,
      properties: {
        player_id: {
          type: "integer",
          minimum: 1,
          description: "Analyticom player ID, for example 8408855.",
        },
        organization_id_filter: {
          type: "integer",
          minimum: 1,
          description: "Analyticom organization ID used by organizationIdFilter, for example 168094.",
        },
      },
      required: ["player_id", "organization_id_filter"],
    },
  },
  {
    name: "get_match_lineups",
    description:
      "Get the Analyticom home and away lineups for one match, including players, starters, substitutes, captains, officials, and embedded player events.",
    inputSchema: {
      type: "object",
      additionalProperties: false,
      properties: {
        match_id: {
          type: "integer",
          minimum: 1,
          description: "Analyticom match ID, for example 400204631.",
        },
        organization_id_filter: {
          type: "integer",
          minimum: 1,
          description: "Analyticom organization ID used by organizationIdFilter, for example 168094.",
        },
      },
      required: ["match_id", "organization_id_filter"],
    },
  },
  {
    name: "get_competition_red_card_stats",
    description:
      "Get Analyticom red-card statistics for a competition and organization. Returns ranked player entries with red-card value and team details.",
    inputSchema: {
      type: "object",
      additionalProperties: false,
      properties: {
        competition_id: {
          type: "integer",
          minimum: 1,
          description: "Analyticom competition ID, for example 400185941.",
        },
        organization_id_filter: {
          type: "integer",
          minimum: 1,
          description: "Analyticom organization ID used by organizationIdFilter, for example 168094.",
        },
      },
      required: ["competition_id", "organization_id_filter"],
    },
  },
  {
    name: "get_competition_yellow_card_stats",
    description:
      "Get Analyticom yellow-card statistics for a competition and organization. Returns ranked player entries with yellow-card value and team details.",
    inputSchema: {
      type: "object",
      additionalProperties: false,
      properties: {
        competition_id: {
          type: "integer",
          minimum: 1,
          description: "Analyticom competition ID, for example 400185941.",
        },
        organization_id_filter: {
          type: "integer",
          minimum: 1,
          description: "Analyticom organization ID used by organizationIdFilter, for example 168094.",
        },
      },
      required: ["competition_id", "organization_id_filter"],
    },
  },
  {
    name: "get_competition_goal_stats",
    description:
      "Get Analyticom goal statistics for a competition and organization. Returns ranked player entries with goal value and team details.",
    inputSchema: {
      type: "object",
      additionalProperties: false,
      properties: {
        competition_id: {
          type: "integer",
          minimum: 1,
          description: "Analyticom competition ID, for example 400185941.",
        },
        organization_id_filter: {
          type: "integer",
          minimum: 1,
          description: "Analyticom organization ID used by organizationIdFilter, for example 168094.",
        },
      },
      required: ["competition_id", "organization_id_filter"],
    },
  },
  {
    name: "list_soccer_matches",
    description:
      "List past soccer matches for an Analyticom competition and organization. Returns the API's paginated result and size fields.",
    inputSchema: {
      type: "object",
      additionalProperties: false,
      properties: {
        competition_id: {
          type: "integer",
          minimum: 1,
          description: "Analyticom competition ID, for example 400185941.",
        },
        organization_id_filter: {
          type: "integer",
          minimum: 1,
          description: "Analyticom organization ID used by organizationIdFilter, for example 168094.",
        },
        page: {
          type: "integer",
          minimum: 1,
          default: 1,
          description: "One-based result page.",
        },
        page_size: {
          type: "integer",
          minimum: 1,
          maximum: 100,
          default: 10,
          description: "Number of matches to return per page.",
        },
      },
      required: ["competition_id", "organization_id_filter"],
    },
  },
  {
    name: "list_future_soccer_matches",
    description:
      "List future scheduled soccer fixtures for an Analyticom competition and organization. Returns the API's paginated result and size fields.",
    inputSchema: {
      type: "object",
      additionalProperties: false,
      properties: {
        competition_id: {
          type: "integer",
          minimum: 1,
          description: "Analyticom competition ID, for example 400185941.",
        },
        organization_id_filter: {
          type: "integer",
          minimum: 1,
          description: "Analyticom organization ID used by organizationIdFilter, for example 168094.",
        },
        page: {
          type: "integer",
          minimum: 1,
          default: 1,
          description: "One-based result page.",
        },
        page_size: {
          type: "integer",
          minimum: 1,
          maximum: 100,
          default: 10,
          description: "Number of fixtures to return per page.",
        },
      },
      required: ["competition_id", "organization_id_filter"],
    },
  },
  {
    name: "submit_request",
    description:
      "Submit an approved request to a path under the configured REST API. The server adds the API_KEY header securely.",
    inputSchema: {
      type: "object",
      additionalProperties: false,
      properties: {
        method: {
          type: "string",
          enum: ["GET", "POST", "PUT", "PATCH", "DELETE"],
          default: "GET",
          description: "HTTP method.",
        },
        path: {
          type: "string",
          pattern: "^/(?!/)",
          description: "Path beneath REST_API_BASE_URL, beginning with '/'.",
        },
        query: {
          type: "object",
          additionalProperties: {
            anyOf: [
              { type: "string" },
              { type: "number" },
              { type: "boolean" },
              {
                type: "array",
                items: { anyOf: [{ type: "string" }, { type: "number" }, { type: "boolean" }] },
              },
            ],
          },
          description: "Optional query parameters. Array values become repeated parameters.",
        },
        body: {
          description: "Optional JSON request body. Not allowed for GET.",
        },
      },
      required: ["path"],
    },
  },
];

async function handle(message) {
  if (!message || message.jsonrpc !== "2.0" || typeof message.method !== "string") {
    return failure(message?.id, -32600, "Invalid Request");
  }

  if (message.id === undefined) return null;

  switch (message.method) {
    case "initialize":
      return success(message.id, {
        protocolVersion: message.params?.protocolVersion ?? "2024-11-05",
        capabilities: { tools: {} },
        serverInfo: { name: SERVER_NAME, version: SERVER_VERSION },
      });
    case "ping":
      return success(message.id, {});
    case "tools/list":
      return success(message.id, { tools });
    case "tools/call": {
      try {
        if (message.params?.name === "get_player_picture") {
          return success(message.id, await getPlayerPicture(message.params.arguments ?? {}));
        }
        if (message.params?.name === "get_player") {
          return success(message.id, await getPlayer(message.params.arguments ?? {}));
        }
        if (message.params?.name === "get_match_lineups") {
          return success(message.id, await getMatchLineups(message.params.arguments ?? {}));
        }
        if (message.params?.name === "get_competition_red_card_stats") {
          return success(message.id, await getCompetitionRedCardStats(message.params.arguments ?? {}));
        }
        if (message.params?.name === "get_competition_yellow_card_stats") {
          return success(message.id, await getCompetitionYellowCardStats(message.params.arguments ?? {}));
        }
        if (message.params?.name === "get_competition_goal_stats") {
          return success(message.id, await getCompetitionGoalStats(message.params.arguments ?? {}));
        }
        if (message.params?.name === "list_soccer_matches") {
          return success(message.id, await listSoccerMatches(message.params.arguments ?? {}));
        }
        if (message.params?.name === "list_future_soccer_matches") {
          return success(message.id, await listFutureSoccerMatches(message.params.arguments ?? {}));
        }
        if (message.params?.name === "submit_request") {
          return success(message.id, await submitRequest(message.params.arguments ?? {}));
        }
        return success(message.id, toolError(`Unknown tool: ${message.params?.name ?? "(missing)"}`));
      } catch (error) {
        const messageText = error?.name === "TimeoutError"
          ? `Request timed out after ${DEFAULT_TIMEOUT_MS} ms.`
          : error instanceof Error
            ? error.message
            : "The request failed.";
        return success(message.id, toolError(messageText));
      }
    }
    default:
      return failure(message.id, -32601, "Method not found");
  }
}

const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
input.on("line", async (line) => {
  if (!line.trim()) return;
  let message;
  try {
    message = JSON.parse(line);
  } catch {
    write(failure(null, -32700, "Parse error"));
    return;
  }

  try {
    const response = await handle(message);
    if (response) write(response);
  } catch (error) {
    write(failure(message?.id, -32603, "Internal error", error instanceof Error ? error.message : undefined));
  }
});
