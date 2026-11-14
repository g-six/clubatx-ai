import { mkdir, open, unlink } from 'node:fs/promises';
import { isAbsolute, join } from 'node:path';
import { createHash } from 'node:crypto';

const BASE = 'https://api-latam.analyticom.de/api/live/CSA_BCS/';
const IMAGE_LIMIT = 5 * 1024 * 1024;

function positive(value, name) {
  if (!Number.isSafeInteger(value) || value <= 0) throw new Error(`${name} must be a positive integer.`);
  return value;
}

function secureBase(value, name) {
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) {
    throw new Error(`${name} must be an HTTPS URL without credentials, query or fragment.`);
  }
  if (!url.pathname.endsWith('/')) url.pathname += '/';
  return url;
}

async function bytes(response, limit) {
  if (!response.body) throw new Error('Empty response.');
  const reader = response.body.getReader();
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > limit) throw new Error('Response exceeds the download size limit.');
      chunks.push(value);
    }
  } finally { await reader.cancel(); }
  return Buffer.concat(chunks);
}

function imageType(data) {
  if (data.subarray(0, 8).equals(Buffer.from('89504e470d0a1a0a', 'hex'))) return ['image/png', 'png'];
  if (data.length >= 3 && data.subarray(0, 3).equals(Buffer.from('ffd8ff', 'hex'))) return ['image/jpeg', 'jpg'];
  if (/^GIF8[79]a$/.test(data.subarray(0, 6).toString('ascii'))) return ['image/gif', 'gif'];
  if (data.length >= 12 && data.toString('ascii', 0, 4) === 'RIFF' && data.toString('ascii', 8, 12) === 'WEBP') return ['image/webp', 'webp'];
  throw new Error('Photo response is not a supported PNG, JPEG, GIF or WebP image.');
}

export async function downloadPhoto(args, { env = process.env, fetchImpl = fetch } = {}) {
  if (!args || typeof args !== 'object' || Array.isArray(args) || Object.keys(args).some(key => !['athlete_slug', 'output_directory', 'organization_id_filter'].includes(key))) {
    throw new Error('Provide only athlete_slug, output_directory and optional organization_id_filter.');
  }
  const slug = args?.athlete_slug;
  if (typeof slug !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) || slug.length > 200) {
    throw new Error('athlete_slug must be the exact ClubATX athlete slug.');
  }
  if (typeof args.output_directory !== 'string' || !isAbsolute(args.output_directory)) {
    throw new Error('output_directory must be an absolute local directory.');
  }
  const org = positive(args.organization_id_filter ?? Number(env.ANALYTICOM_ORGANIZATION_ID ?? 168094), 'organization_id_filter');
  const supabaseUrl = env.SUPABASE_URL || env.NEXT_PUBLIC_SUPABASE_URL;
  if (!supabaseUrl || !env.SUPABASE_SERVICE_ROLE_KEY || !env.REST_API_KEY) {
    throw new Error('Configure SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY and REST_API_KEY in the local server environment.');
  }
  const db = secureBase(supabaseUrl, 'SUPABASE_URL');
  const api = secureBase(env.REST_API_BASE_URL || BASE, 'REST_API_BASE_URL');
  async function request(url, headers, limit = 1024 * 1024) {
    let response;
    try {
      response = await fetchImpl(url, { method: 'GET', headers, redirect: 'manual', signal: AbortSignal.timeout(30_000) });
    } catch { throw new Error('Upstream request failed or timed out. Check the local connection and configuration.'); }
    if (!response.ok) {
      await response.body?.cancel();
      throw new Error(`Upstream request failed (HTTP ${response.status}); no photo saved.`);
    }
    return { data: await bytes(response, limit), type: response.headers.get('content-type') || '' };
  }
  async function rows(table, query) {
    const url = new URL(`rest/v1/${table}`, db);
    url.search = new URLSearchParams(query).toString();
    const headers = { apikey: env.SUPABASE_SERVICE_ROLE_KEY, Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}` };
    const result = JSON.parse((await request(url, headers)).data.toString('utf8'));
    if (!Array.isArray(result)) throw new Error('Unexpected database response.');
    return result;
  }
  const athletes = await rows('athletes', { select: 'slug,first_name,last_name', slug: `eq.${slug}`, limit: '2' });
  if (athletes.length !== 1) throw new Error('Exact athlete record not found or ambiguous.');
  const links = await rows('analyticom_player_links', { select: 'person_id,athlete_slug', athlete_slug: `eq.${slug}`, limit: '2' });
  if (links.length !== 1 || links[0].athlete_slug !== slug) throw new Error('Athlete must have exactly one saved Analyticom player link.');
  const personId = positive(Number(links[0].person_id), 'linked person_id');
  const headers = {
    API_KEY: env.REST_API_KEY, Accept: '*/*', 'Accept-Language': 'en',
    'User-Agent': 'BC%20Soccer/8 CFNetwork/3896.100.1.2.1 Darwin/27.0.0', Cookie: 'SRVNAME=d21',
  };
  function analyticUrl(path) {
    const url = new URL(path, api);
    url.searchParams.set('organizationIdFilter', String(org));
    return url;
  }
  const player = JSON.parse((await request(analyticUrl(`player/${personId}`), headers)).data.toString('utf8'));
  if (!player || typeof player !== 'object' || Array.isArray(player)) throw new Error('Unexpected player response.');
  if (player.hideProfile === true) throw new Error('Analyticom profile is hidden; photo unavailable.');
  if (player.personId != null && Number(player.personId) !== personId) throw new Error('Analyticom player identity does not match the saved link.');
  const picture = player.picture;
  if (typeof picture !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(picture) || picture === '.' || picture === '..') {
    throw new Error('Linked Analyticom player has no usable picture identifier.');
  }
  const response = await request(analyticUrl(`images/${encodeURIComponent(picture)}`), headers, 8 * 1024 * 1024);
  let data = response.data;
  if (response.type.toLowerCase().includes('application/json')) {
    const envelope = JSON.parse(data.toString('utf8'));
    const value = typeof envelope?.value === 'string' ? envelope.value.replace(/\s/g, '') : '';
    if (!value || value.length % 4 !== 0 || !/^[A-Za-z0-9+/]*={0,2}$/.test(value)) throw new Error('Invalid base64 photo response.');
    data = Buffer.from(value, 'base64');
    if (data.toString('base64') !== value) throw new Error('Invalid base64 photo response.');
  }
  if (!data.length || data.length > IMAGE_LIMIT) throw new Error('Photo is empty or exceeds 5 MiB.');
  const [mimeType, extension] = imageType(data);
  // Recheck the persistent link before writing in case it changed during the download.
  const current = await rows('analyticom_player_links', { select: 'person_id,athlete_slug', athlete_slug: `eq.${slug}`, limit: '2' });
  if (current.length !== 1 || current[0].athlete_slug !== slug || Number(current[0].person_id) !== personId) {
    throw new Error('Athlete link changed during download; no photo saved.');
  }
  await mkdir(args.output_directory, { recursive: true });
  const file = join(args.output_directory, `${slug}-analyticom-${personId}.${extension}`);
  const handle = await open(file, 'wx', 0o600);
  try { await handle.writeFile(data); }
  catch (error) { await handle.close(); await unlink(file); throw error; }
  await handle.close();
  return {
    athlete_slug: slug,
    athlete_name: [athletes[0].first_name, athletes[0].last_name].filter(Boolean).join(' '),
    person_id: personId, organization_id_filter: org, picture,
    path: file, mime_type: mimeType, byte_length: data.length,
    sha256: createHash('sha256').update(data).digest('hex'), downloaded_at: new Date().toISOString(),
  };
}
