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
  console.error("\n[build] Variáveis ausentes para o Vite (Firebase):\n");
  missing.forEach((k) => console.error(`  - ${k}`));
  console.error(
    "\nNo Render: Environment → adicione cada VITE_FIREBASE_* → Manual Deploy.\n" +
      "Local: copie de .env.example para .env\n"
  );
  process.exit(1);
}
