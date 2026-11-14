#!/usr/bin/env node
import readline from 'node:readline';
import { downloadPhoto } from './photo.mjs';

const tool = {
  name: 'download_linked_player_photo',
  description: 'Download the original Analyticom photo for an exact ClubATX athlete slug using its saved player link. Reads athlete/link records and creates one local image file; does not update the athlete photo or database. Requires local server credentials.',
  annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: true },
  inputSchema: {
    type: 'object', additionalProperties: false,
    properties: {
      athlete_slug: { type: 'string', description: 'Exact existing ClubATX athlete slug.' },
      output_directory: { type: 'string', description: 'Absolute local directory for the downloaded photo. Existing files are never overwritten.' },
      organization_id_filter: { type: 'integer', minimum: 1, description: 'Analyticom organization ID. Defaults to configured ANALYTICOM_ORGANIZATION_ID or ClubATX BC Soccer organization 168094.' },
    },
    required: ['athlete_slug', 'output_directory'],
  },
};
async function handle(message) {
  if (!message || typeof message !== 'object' || message.jsonrpc !== '2.0' || typeof message.method !== 'string') {
    return { jsonrpc: '2.0', id: message?.id ?? null, error: { code: -32600, message: 'Invalid request' } };
  }
  const { id, method, params } = message;
  if (id === undefined) return;
  const reply = (result) => ({ jsonrpc: '2.0', id, result });
  if (method === 'initialize') return reply({ protocolVersion: params?.protocolVersion ?? '2024-11-05', capabilities: { tools: {} }, serverInfo: { name: 'analyticom-player-photo', version: '0.1.0' } });
  if (method === 'ping') return reply({});
  if (method === 'tools/list') return reply({ tools: [tool] });
  if (method === 'tools/call') {
    try {
      if (params?.name !== tool.name) throw new Error('Unknown tool.');
      const result = await downloadPhoto(params.arguments);
      return reply({ content: [{ type: 'text', text: JSON.stringify(result) }], structuredContent: result });
    } catch (error) {
      const text = error?.code === 'EEXIST' ? 'Photo file already exists; choose another output directory.' : error instanceof SyntaxError ? 'Upstream returned malformed JSON; no photo saved.' : error.message || 'Photo download failed.';
      return reply({ isError: true, content: [{ type: 'text', text }] });
    }
  }
  return { jsonrpc: '2.0', id, error: { code: -32601, message: 'Method not found' } };
}
const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of input) {
  if (!line.trim()) continue;
  let message;
  try { message = JSON.parse(line); }
  catch { process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } }) + '\n'); continue; }
  const result = await handle(message);
  if (result) process.stdout.write(JSON.stringify(result) + '\n');
}
