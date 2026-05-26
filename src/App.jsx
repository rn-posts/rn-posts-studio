import { useState } from "react";
import PostQueue from "./components/PostQueue";
import PostEditor from "./components/PostEditor";
import History from "./components/History";
import Sidebar from "./components/Sidebar";
import { firebaseConfigError } from "./firebase";
import "./styles/global.css";

export default function App() {
  if (firebaseConfigError) {
    return (
      <div className="app-shell">
        <main className="main-content" style={{ padding: "2rem", maxWidth: 560 }}>
          <h1 style={{ marginBottom: "1rem" }}>Configuração Firebase</h1>
          <p style={{ lineHeight: 1.6 }}>{firebaseConfigError}</p>
          <p style={{ marginTop: "1rem", lineHeight: 1.6, opacity: 0.85 }}>
            No Render: <strong>Environment</strong> → adicione as variáveis{" "}
            <code>VITE_FIREBASE_*</code> (mesmos valores do seu arquivo <code>.env</code> local) →{" "}
            <strong>Manual Deploy</strong>.
          </p>
        </main>
      </div>
    );
  }

  const [activePage, setActivePage] = useState("queue");
  const [editingPost, setEditingPost] = useState(null);
  const [notification, setNotification] = useState(null);

  const showNotification = (msg, type = "success") => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 3500);
  };

  const handleEdit = (post) => {
    setEditingPost(post);
    setActivePage("editor");
  };

  const handleEditorClose = () => {
    setEditingPost(null);
    setActivePage("queue");
  };

  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} setActivePage={setActivePage} />

      <main className="main-content">
        {notification && (
          <div className={`toast toast--${notification.type}`}>
            {notification.msg}
          </div>
        )}

        {activePage === "queue" && (
          <PostQueue
            onEdit={handleEdit}
            onNotify={showNotification}
          />
        )}
        {activePage === "editor" && (
          <PostEditor
            post={editingPost}
            onClose={handleEditorClose}
            onNotify={showNotification}
          />
        )}
        {activePage === "history" && (
          <History onNotify={showNotification} />
        )}
      </main>
    </div>
  );
}
