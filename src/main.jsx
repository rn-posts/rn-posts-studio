import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/global.css";
import App from "./App.jsx";
import { initFirebase, firebaseConfigError } from "./firebase";

const rootEl = document.getElementById("root");
const root = createRoot(rootEl);

function showBootError(msg) {
  root.render(
    <div style={{ padding: "2rem", fontFamily: "system-ui", maxWidth: 560 }}>
      <h1>Configuração Firebase</h1>
      <p style={{ lineHeight: 1.6 }}>{msg}</p>
      <p style={{ marginTop: "1rem", opacity: 0.85, lineHeight: 1.6 }}>
        No Render → <strong>rn-posts</strong> → <strong>Environment</strong> → adicione{" "}
        <code>FIREBASE_API_KEY</code>, <code>FIREBASE_AUTH_DOMAIN</code>, etc. (valores do seu{" "}
        <code>.env</code>) → <strong>Save and deploy</strong>.
      </p>
    </div>
  );
}

initFirebase()
  .then(() => {
    root.render(
      <StrictMode>
        <App />
      </StrictMode>
    );
  })
  .catch((e) => {
    showBootError(e.message || firebaseConfigError || "Erro ao iniciar Firebase");
  });
