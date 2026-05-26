/**
 * Falha o build se variáveis do Firebase não estiverem definidas (ex.: Render sem env vars).
 */
const required = [
  "VITE_FIREBASE_API_KEY",
  "VITE_FIREBASE_AUTH_DOMAIN",
  "VITE_FIREBASE_PROJECT_ID",
  "VITE_FIREBASE_STORAGE_BUCKET",
  "VITE_FIREBASE_MESSAGING_SENDER_ID",
  "VITE_FIREBASE_APP_ID",
];

const missing = required.filter((k) => !process.env[k]?.trim());

if (missing.length) {
  const viteKeys = Object.keys(process.env).filter((k) => k.startsWith("VITE_"));
  console.error("\n[build] Variáveis ausentes para o Vite (Firebase):\n");
  missing.forEach((k) => console.error(`  - ${k}`));
  console.error(
    `\n[build] VITE_* presentes no servidor: ${
      viteKeys.length ? viteKeys.join(", ") : "(nenhuma — Environment não foi salvo no Render)"
    }\n`
  );
  console.error(
    "No Render: rn-posts → Environment → adicione VITE_FIREBASE_* → Save, rebuild and deploy.\n" +
      "Local: copie de .env.example para .env\n"
  );
  process.exit(1);
}
