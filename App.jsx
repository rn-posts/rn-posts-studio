import { useState, useEffect } from "react";
import PostQueue from "./components/PostQueue";
import PostEditor from "./components/PostEditor";
import History from "./components/History";
import Sidebar from "./components/Sidebar";
import "./styles/global.css";

export default function App() {
  const [activePage, setActivePage] = useState("queue");
  const [editingPost, setEditingPost] = useState(null);
  const [posts, setPosts] = useState([]);
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
            posts={posts}
            setPosts={setPosts}
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
