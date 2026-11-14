import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { downloadPhoto } from '../scripts/photo.mjs';

const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aK2kAAAAASUVORK5CYII=', 'base64');
const env = { SUPABASE_URL: 'https://db.example', SUPABASE_SERVICE_ROLE_KEY: 'db-secret', REST_API_KEY: 'api-secret' };
async function fixture(t, overrides = {}) {
  const dir = await mkdtemp(join(tmpdir(), 'analyticom-photo-test-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const calls = [];
  let links = 0;
  const fetchImpl = async (input, options) => {
    const url = new URL(input);
    calls.push({ url, ...options });
    assert.equal(options.method, 'GET');
    assert.equal(options.redirect, 'manual');
    if (url.host === 'db.example') {
      assert.equal(options.headers.apikey, 'db-secret');
      assert.equal(options.headers.API_KEY, undefined);
      assert.equal(url.searchParams.get('limit'), '2');
      if (url.pathname.endsWith('/athletes')) return Response.json(overrides.athletes ?? [{ slug: 'test-athlete', first_name: 'Test', last_name: 'Athlete' }]);
      assert.equal(url.searchParams.get('athlete_slug'), 'eq.test-athlete');
      links++;
      return Response.json(links > 1 && overrides.changed ? [] : (overrides.links ?? [{ person_id: 42, athlete_slug: 'test-athlete' }]));
    }
    assert.equal(url.host, 'api-latam.analyticom.de');
    assert.equal(options.headers.API_KEY, 'api-secret');
    assert.equal(options.headers.apikey, undefined);
    assert.equal(url.searchParams.get('organizationIdFilter'), '168094');
    if (url.pathname.endsWith('/player/42')) return Response.json(overrides.player ?? { personId: 42, picture: 'photo-id' });
    assert.ok(url.pathname.endsWith('/images/photo-id'));
    return overrides.image?.() ?? Response.json({ contentType: 'image/png', value: png.toString('base64'), pictureLink: 'https://untrusted.example/never-follow' });
  };
  return { dir, calls, options: { env, fetchImpl }, args: { athlete_slug: 'test-athlete', output_directory: dir } };
}

test('saved athlete link downloads exact original bytes and never overwrites', async t => {
  const f = await fixture(t);
  const result = await downloadPhoto(f.args, f.options);
  assert.equal(result.person_id, 42);
  assert.equal(result.mime_type, 'image/png');
  assert.equal(result.byte_length, png.length);
  assert.match(result.sha256, /^[a-f0-9]{64}$/);
  assert.deepEqual(await readFile(result.path), png);
  assert.equal(f.calls.length, 5);
  await assert.rejects(downloadPhoto(f.args, f.options), { code: 'EEXIST' });
  assert.deepEqual(await readFile(result.path), png);
});
test('binary photo response works', async t => {
  const f = await fixture(t, { image: () => new Response(png, { headers: { 'content-type': 'image/png' } }) });
  assert.deepEqual(await readFile((await downloadPhoto(f.args, f.options)).path), png);
});
for (const [name, overrides, pattern] of [
  ['missing athlete', { athletes: [] }, /athlete record/],
  ['missing link', { links: [] }, /exactly one/],
  ['ambiguous link', { links: [{ person_id: 42 }, { person_id: 43 }] }, /exactly one/],
  ['hidden profile', { player: { hideProfile: true, picture: 'photo-id' } }, /hidden/],
  ['missing picture', { player: { personId: 42 } }, /picture identifier/],
  ['mismatched identity', { player: { personId: 43, picture: 'photo-id' } }, /identity/],
  ['picture traversal', { player: { picture: '..' } }, /picture identifier/],
  ['link changed', { changed: true }, /link changed/],
  ['HTML masquerading as image', { image: () => new Response('<html>login</html>', { headers: { 'content-type': 'image/png' } }) }, /supported/],
  ['invalid base64', { image: () => Response.json({ value: '!!!' }) }, /base64/],
  ['redirect', { image: () => new Response(null, { status: 302, headers: { location: 'https://other.example' } }) }, /HTTP 302/],
  ['authentication error', { image: () => new Response('private upstream message', { status: 401 }) }, /HTTP 401/],
  ['oversized response', { image: () => new Response(Buffer.alloc(8 * 1024 * 1024 + 1)) }, /size limit/],
]) {
  test(`${name} fails without saving`, async t => {
    const f = await fixture(t, overrides);
    await assert.rejects(downloadPhoto(f.args, f.options), pattern);
    assert.deepEqual(await readdir(f.dir), []);
  });
}
test('rejects invalid input and missing credentials before network access', async () => {
  const options = { env: {}, fetchImpl: () => assert.fail('Unexpected network call') };
  for (const args of [{ athlete_slug: '../x', output_directory: '/tmp' }, { athlete_slug: 'test-athlete', output_directory: 'relative' }, { athlete_slug: 'test-athlete', output_directory: '/tmp', organization_id_filter: 0 }, { athlete_slug: 'test-athlete', output_directory: '/tmp' }]) {
    await assert.rejects(downloadPhoto(args, options));
  }
});
test('stdio server initializes, lists tool, and handles errors without leaking keys', () => {
  const messages = [
    { jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05' } },
    { jsonrpc: '2.0', method: 'notifications/initialized' },
    { jsonrpc: '2.0', id: 2, method: 'tools/list' },
    { jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'download_linked_player_photo', arguments: {} } },
  ];
  const result = spawnSync(process.execPath, [new URL('../scripts/server.mjs', import.meta.url).pathname], { input: messages.map(JSON.stringify).join('\n') + '\n', encoding: 'utf8', env: { ...process.env, ...env } });
  assert.equal(result.status, 0, result.stderr);
  const replies = result.stdout.trim().split('\n').map(JSON.parse);
  assert.equal(replies.length, 3);
  assert.equal(replies[0].result.serverInfo.name, 'analyticom-player-photo');
  assert.equal(replies[1].result.tools[0].name, 'download_linked_player_photo');
  assert.equal(replies[2].result.isError, true);
  assert.ok(!result.stdout.includes('db-secret') && !result.stdout.includes('api-secret'));
});
