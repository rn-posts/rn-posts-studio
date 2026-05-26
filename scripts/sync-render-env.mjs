/**
 * Envia variáveis do .env local para o serviço Render (rn-posts).
 *
 * Uso:
 *   1. Crie API key em https://dashboard.render.com/u/settings#api-keys
 *   2. No PowerShell: $env:RENDER_API_KEY = "rnd_..."
 *   3. node scripts/sync-render-env.mjs
 *
 * Opcional: $env:RENDER_SERVICE_ID = "srv_..." (senão busca por nome rn-posts)
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");
const ENV_FILE = path.join(ROOT, ".env");

const API_KEY = process.env.RENDER_API_KEY;
const SERVICE_NAME = process.env.RENDER_SERVICE_NAME || "rn-posts";

/** Chaves usadas no build (Vite) ou runtime (Python). */
const ALLOW = new Set([
  "VITE_FIREBASE_API_KEY",
  "VITE_FIREBASE_AUTH_DOMAIN",
  "VITE_FIREBASE_PROJECT_ID",
  "VITE_FIREBASE_STORAGE_BUCKET",
  "VITE_FIREBASE_MESSAGING_SENDER_ID",
  "VITE_FIREBASE_APP_ID",
  "VITE_MAKE_WEBHOOK_URL",
  "CLOUDINARY_CLOUD_NAME",
  "CLOUDINARY_API_KEY",
  "CLOUDINARY_API_SECRET",
  "GEMINI_API_KEY",
  "GROQ_API_KEY",
  "GOOGLE_SERVICE_ACCOUNT_JSON",
]);

function parseEnv(text) {
  const out = {};
  for (const line of text.split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const i = t.indexOf("=");
    if (i < 1) continue;
    const key = t.slice(0, i).trim();
    let val = t.slice(i + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (ALLOW.has(key) && val) out[key] = val;
  }
  return out;
}

async function api(path, opts = {}) {
  const res = await fetch(`https://api.render.com/v1${path}`, {
    ...opts,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_KEY}`,
      ...opts.headers,
    },
  });
  const body = await res.text();
  let json;
  try {
    json = body ? JSON.parse(body) : null;
  } catch {
    json = body;
  }
  if (!res.ok) {
    throw new Error(`${res.status} ${path}: ${typeof json === "object" ? JSON.stringify(json) : body}`);
  }
  return json;
}

async function findServiceId() {
  if (process.env.RENDER_SERVICE_ID) return process.env.RENDER_SERVICE_ID;
  let cursor;
  do {
    const q = new URLSearchParams({ limit: "100" });
    if (cursor) q.set("cursor", cursor);
    const data = await api(`/services?${q}`);
    for (const row of data || []) {
      const s = row.service || row;
      const name = s.name || "";
      const slug = s.slug || "";
      if (
        name === SERVICE_NAME ||
        slug === SERVICE_NAME ||
        (s.serviceDetails?.url || "").includes("rn-posts.onrender.com")
      ) {
        return s.id;
      }
    }
    cursor = data?.[data.length - 1]?.cursor;
  } while (cursor);
  throw new Error(`Serviço "${SERVICE_NAME}" não encontrado. Defina RENDER_SERVICE_ID=srv_...`);
}

async function main() {
  if (!API_KEY) {
    console.error("Defina RENDER_API_KEY (https://dashboard.render.com/u/settings#api-keys)");
    process.exit(1);
  }
  if (!fs.existsSync(ENV_FILE)) {
    console.error(`Arquivo não encontrado: ${ENV_FILE}`);
    process.exit(1);
  }

  const vars = parseEnv(fs.readFileSync(ENV_FILE, "utf8"));
  const keys = Object.keys(vars);
  if (!keys.length) {
    console.error("Nenhuma variável relevante no .env");
    process.exit(1);
  }

  const serviceId = await findServiceId();
  console.log(`Serviço: ${serviceId}`);
  console.log(`Enviando ${keys.length} variáveis...`);

  for (const [key, value] of Object.entries(vars)) {
    await api(`/services/${serviceId}/env-vars/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: JSON.stringify({ key, value }),
    });
    console.log(`  OK ${key}`);
  }

  console.log("\nDisparando deploy...");
  await api(`/services/${serviceId}/deploys`, {
    method: "POST",
    body: JSON.stringify({ clearCache: "do_not_clear" }),
  });
  console.log("Deploy iniciado. Aguarde ~3–5 min e teste o site.");
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
