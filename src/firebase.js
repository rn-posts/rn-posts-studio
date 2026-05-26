import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

export let db = null;
export let firebaseConfigError = null;

function configFromViteEnv() {
  const apiKey = import.meta.env.VITE_FIREBASE_API_KEY;
  if (!apiKey?.trim()) return null;
  return {
    apiKey,
    authDomain:        import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId:         import.meta.env.VITE_FIREBASE_PROJECT_ID,
    storageBucket:     import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
    appId:             import.meta.env.VITE_FIREBASE_APP_ID,
  };
}

/** Carrega Firebase: .env local (dev) ou /config/firebase no Render (runtime). */
export async function initFirebase() {
  if (db) return db;

  let cfg = configFromViteEnv();
  if (!cfg) {
    const res = await fetch("/config/firebase");
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      firebaseConfigError = data.erro || data.dica || `HTTP ${res.status}`;
      throw new Error(firebaseConfigError);
    }
    cfg = data;
  }

  const app = initializeApp(cfg);
  db = getFirestore(app);
  return db;
}
