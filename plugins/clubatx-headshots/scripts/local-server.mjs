import { createInterface } from 'node:readline';
import worker from '../worker/index.js';

if (process.env.CLUBATX_HEADSHOTS_ENV_FILE) {
  process.loadEnvFile(process.env.CLUBATX_HEADSHOTS_ENV_FILE);
}
const input = createInterface({ input: process.stdin, crlfDelay: Infinity });
input.on('line', async (line) => {
  let rpc;
  try {
    rpc = JSON.parse(line);
    const response = await worker.fetch(new Request('http://localhost/mcp', {
      method: 'POST', body: line,
    }), process.env);
    if (rpc.id === undefined) return;
    const result = await response.json();
    // Negotiate the client's version for the local stdio transport.
    if (rpc.method === 'initialize' && result.result && rpc.params?.protocolVersion) {
      result.result.protocolVersion = rpc.params.protocolVersion;
    }
    process.stdout.write(JSON.stringify(result) + '\n');
  } catch {
    process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: rpc?.id ?? null,
      error: { code: -32603, message: 'Local headshot tool request failed' } }) + '\n');
  }
});
