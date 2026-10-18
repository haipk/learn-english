/**
 * DinoB Lab API — dinob.io.vn
 *
 * Worker phục vụ static assets (ASSETS) + REST API:
 *   GET  /api/data           -> {k: v} toàn bộ bảng kv (đọc public)
 *   PUT  /api/data           -> upsert {k: v} vào D1 (cần Bearer ADMIN_TOKEN)
 *   GET  /api/media          -> liệt kê object trong R2 (đọc public)
 *   GET  /api/media/<name>   -> tải 1 file media từ R2 (đọc public)
 *   PUT  /api/media/<name>   -> upload file media lên R2 (cần token)
 *   GET  /api/backup         -> tải backup sqlite từ R2 (đọc public)
 *   PUT  /api/backup         -> ghi backup sqlite lên R2 (cần token)
 * Mọi path khác -> file tĩnh trong ./public qua binding ASSETS.
 */

const SKIP_KEYS = new Set(["dinob_sqlite", "dinob_apitoken"]);
const BACKUP_KEY = "backup/dinob-data.sqlite";
const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

const json = (data, init) =>
  new Response(JSON.stringify(data), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init?.headers || {}) },
  });

function authed(req, env) {
  const tok = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
  return !!env.ADMIN_TOKEN && tok === env.ADMIN_TOKEN;
}

async function getData(env) {
  const { results } = await env.DB.prepare("SELECT k, v FROM kv").all();
  const out = {};
  for (const r of results) out[r.k] = r.v;
  return out;
}

async function putData(req, env) {
  const body = await req.json();
  if (!body || typeof body !== "object" || Array.isArray(body))
    return json({ ok: false, error: "body phải là object {k: v}" }, { status: 400 });
  const stmts = Object.entries(body)
    .filter(([k, v]) => !SKIP_KEYS.has(k) && typeof v === "string")
    .map(([k, v]) => env.DB.prepare("INSERT OR REPLACE INTO kv(k, v) VALUES(?, ?)").bind(k, v));
  for (let i = 0; i < stmts.length; i += 100)   // batch tối đa 100 stmt/lần
    await env.DB.batch(stmts.slice(i, i + 100));
  return json({ ok: true, written: stmts.length });
}

async function listMedia(env) {
  if (!env.MEDIA) return json({ ok: false, error: "R2 chưa được bật" }, { status: 503 });
  const out = [];
  let cursor;
  do {
    const page = await env.MEDIA.list({ prefix: "media/", cursor, limit: 1000 });
    for (const o of page.objects) out.push({ name: o.key.slice(6), size: o.size, etag: o.etag });
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);
  return json({ ok: true, files: out });
}

async function getMedia(env, name) {
  if (!env.MEDIA) return new Response("R2 not enabled", { status: 503, headers: cors });
  const obj = await env.MEDIA.get("media/" + name);
  if (!obj) return new Response("not found", { status: 404, headers: cors });
  const headers = new Headers(cors);
  headers.set("Content-Type", obj.httpMetadata?.contentType || "application/octet-stream");
  headers.set("ETag", obj.etag);
  headers.set("Cache-Control", "public, max-age=86400");
  return new Response(obj.body, { headers });
}

async function putMedia(req, env, name) {
  if (!env.MEDIA) return json({ ok: false, error: "R2 chưa được bật" }, { status: 503 });
  if (!/^[\w.\-]{1,200}$/.test(name)) return json({ ok: false, error: "tên file không hợp lệ" }, { status: 400 });
  await env.MEDIA.put("media/" + name, req.body, {
    httpMetadata: { contentType: req.headers.get("Content-Type") || "application/octet-stream" },
  });
  return json({ ok: true });
}

async function getBackup(env) {
  if (!env.MEDIA) return new Response("R2 not enabled", { status: 503, headers: cors });
  const obj = await env.MEDIA.get(BACKUP_KEY);
  if (!obj) return new Response("not found", { status: 404, headers: cors });
  const headers = new Headers(cors);
  headers.set("Content-Type", "application/octet-stream");
  return new Response(obj.body, { headers });
}

async function putBackup(req, env) {
  if (!env.MEDIA) return json({ ok: false, error: "R2 chưa được bật" }, { status: 503 });
  await env.MEDIA.put(BACKUP_KEY, req.body, {
    httpMetadata: { contentType: "application/octet-stream" },
  });
  return json({ ok: true });
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const p = url.pathname;
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });

    if (p === "/api/data") {
      if (req.method === "GET") return json(await getData(env));
      if (req.method === "PUT") {
        if (!authed(req, env)) return json({ ok: false, error: "sai token" }, { status: 401 });
        return putData(req, env);
      }
    }
    if (p === "/api/media") {
      if (req.method === "GET") return listMedia(env);
    }
    if (p.startsWith("/api/media/")) {
      const name = p.slice(11);
      if (req.method === "GET") return getMedia(env, name);
      if (req.method === "PUT") {
        if (!authed(req, env)) return json({ ok: false, error: "sai token" }, { status: 401 });
        return putMedia(req, env, name);
      }
    }
    if (p === "/api/backup") {
      if (req.method === "GET") return getBackup(env);
      if (req.method === "PUT") {
        if (!authed(req, env)) return json({ ok: false, error: "sai token" }, { status: 401 });
        return putBackup(req, env);
      }
    }
    if (p.startsWith("/api/")) return json({ ok: false, error: "not found" }, { status: 404 });
    return env.ASSETS.fetch(req);
  },
};
