import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Clock,
  FileDiff,
  FilePlus,
  FileText,
  History,
  Lock,
  Mail,
  RefreshCcw,
  RotateCcw,
  Save,
  Split,
  Trash2,
  Users,
} from "lucide-react";
import "./styles.css";
import { createCollabSocket } from "./collabSocket";

const tokenKey = "notgoogledocs_token";
const clientIdKey = "notgoogledocs_client_id";

function App() {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(() => localStorage.getItem(tokenKey) || "");
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");

  const isRegistering = mode === "register";
  const canSubmit = email.trim() && password.length >= 8 && status !== "loading";

  useEffect(() => {
    if (!token) {
      return;
    }

    setStatus("loading");
    api("/api/auth/me", { token })
      .then((data) => {
        setUser(data.user);
        setMessage("");
      })
      .catch(() => {
        localStorage.removeItem(tokenKey);
        setToken("");
      })
      .finally(() => setStatus("idle"));
  }, [token]);

  const title = useMemo(
    () => (isRegistering ? "Create your workspace" : "Sign in to NotGoogleDocs"),
    [isRegistering],
  );

  async function handleSubmit(event) {
    event.preventDefault();
    setStatus("loading");
    setMessage("");

    try {
      const data = await api(isRegistering ? "/api/auth/register" : "/api/auth/login", {
        method: "POST",
        body: { email, password },
      });
      localStorage.setItem(tokenKey, data.token);
      setToken(data.token);
      setUser(data.user);
      setPassword("");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setStatus("idle");
    }
  }

  function handleSignOut() {
    localStorage.removeItem(tokenKey);
    setToken("");
    setUser(null);
    setMode("login");
    setEmail("");
    setPassword("");
    setMessage("");
  }

  if (user && token) {
    return <Workspace token={token} user={user} onSignOut={handleSignOut} />;
  }

  return (
    <main className="auth-shell">
      <section className="brand-panel" aria-label="NotGoogleDocs product preview">
        <div className="topbar">
          <div className="brand-mark">
            <FileText size={20} aria-hidden="true" />
          </div>
          <span>NotGoogleDocs</span>
        </div>
        <div className="document-preview">
          <div className="doc-toolbar">
            <span />
            <span />
            <span />
          </div>
          <div className="doc-page">
            <div className="doc-title" />
            <div className="doc-line long" />
            <div className="doc-line" />
            <div className="doc-line medium" />
            <div className="diff-row">
              <span className="removed">Removed paragraph</span>
              <span className="added">Clearer replacement</span>
            </div>
            <div className="doc-line short" />
          </div>
        </div>
      </section>

      <section className="auth-panel" aria-labelledby="auth-title">
        <div>
          <p className="eyebrow">Versioned collaboration</p>
          <h1 id="auth-title">{title}</h1>
          <p className="supporting-copy">
            Save deliberate document snapshots now. Compare thoughtful revisions next.
          </p>
        </div>

        <div className="mode-switch" role="tablist" aria-label="Authentication mode">
          <button
            className={mode === "login" ? "active" : ""}
            onClick={() => {
              setMode("login");
              setMessage("");
            }}
            role="tab"
            aria-selected={mode === "login"}
            type="button"
          >
            Sign in
          </button>
          <button
            className={mode === "register" ? "active" : ""}
            onClick={() => {
              setMode("register");
              setMessage("");
            }}
            role="tab"
            aria-selected={mode === "register"}
            type="button"
          >
            Register
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            <span>Email</span>
            <div className="input-row">
              <Mail size={18} aria-hidden="true" />
              <input
                autoComplete="email"
                name="email"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="sid@example.com"
                type="email"
                value={email}
              />
            </div>
          </label>

          <label>
            <span>Password</span>
            <div className="input-row">
              <Lock size={18} aria-hidden="true" />
              <input
                autoComplete={isRegistering ? "new-password" : "current-password"}
                name="password"
                onChange={(event) => setPassword(event.target.value)}
                placeholder="At least 8 characters"
                type="password"
                value={password}
              />
            </div>
          </label>

          {message ? <p className="form-message">{message}</p> : null}

          <button className="primary-action" disabled={!canSubmit} type="submit">
            {status === "loading" ? (
              <>
                <RefreshCcw className="spinner" size={18} aria-hidden="true" />
                Working
              </>
            ) : isRegistering ? (
              "Create account"
            ) : (
              "Sign in"
            )}
          </button>
        </form>
      </section>
    </main>
  );
}

function Workspace({ token, user, onSignOut }) {
  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftContent, setDraftContent] = useState("");
  const [commitMessage, setCommitMessage] = useState("");
  const [versions, setVersions] = useState([]);
  const [fromVersionId, setFromVersionId] = useState("");
  const [toVersionId, setToVersionId] = useState("");
  const [diff, setDiff] = useState(null);
  const [isCompareOpen, setIsCompareOpen] = useState(false);
  const [autoSaveState, setAutoSaveState] = useState("idle");
  const [collabEnabled, setCollabEnabled] = useState(false);
  const [collabRevision, setCollabRevision] = useState(0);
  const [collabState, setCollabState] = useState("idle");
  const [shareEmail, setShareEmail] = useState("");
  const [shareState, setShareState] = useState("idle");
  const [deletingVersionId, setDeletingVersionId] = useState(null);
  const [status, setStatus] = useState("loading");
  const [notice, setNotice] = useState("");
  const [collabClientId] = useState(() => getOrCreateClientId());
  const lastSavedDraftRef = useRef({ id: null, title: "", content: "" });
  const lastSyncedCollabRef = useRef({ id: null, content: "", revision: 0 });
  const draftContentRef = useRef("");
  const selectedDocumentIdRef = useRef(null);
  const collabSubmittingRef = useRef(false);
  const collabSocketRef = useRef(null);
  const pendingCollabSubmitRef = useRef(null);
  const collabAckTimeoutRef = useRef(null);

  const selectedDocument = documents.find((document) => document.id === selectedDocumentId);
  const canSaveVersion =
    Boolean(selectedDocumentId) && status !== "saving" && status !== "deleting";
  const hasComparableVersions = versions.length >= 2;

  useEffect(() => {
    refreshDocuments();
  }, []);

  useEffect(() => {
    selectedDocumentIdRef.current = selectedDocumentId;
  }, [selectedDocumentId]);

  useEffect(() => {
    draftContentRef.current = draftContent;
  }, [draftContent]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      refreshDocuments({ silent: true });
    }, 3000);

    function handleFocus() {
      refreshDocuments({ silent: true });
    }

    window.addEventListener("focus", handleFocus);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", handleFocus);
    };
  }, [token]);

  useEffect(() => {
    if (!selectedDocumentId) {
      return;
    }

    setCollabEnabled(false);
    setCollabRevision(0);
    setCollabState("idle");
    setShareEmail("");
    setShareState("idle");
    lastSyncedCollabRef.current = { id: null, content: "", revision: 0 };
    loadDocument(selectedDocumentId);
    loadVersions(selectedDocumentId);
  }, [selectedDocumentId]);

  useEffect(() => {
    if (
      !isCompareOpen ||
      !selectedDocumentId ||
      !fromVersionId ||
      !toVersionId ||
      fromVersionId === toVersionId
    ) {
      setDiff(null);
      return;
    }

    api(`/api/documents/${selectedDocumentId}/diff?from=${fromVersionId}&to=${toVersionId}`, {
      token,
    })
      .then(setDiff)
      .catch((error) => {
        setDiff(null);
        setNotice(error.message);
      });
  }, [fromVersionId, isCompareOpen, selectedDocumentId, toVersionId, token]);

  useEffect(() => {
    if (!selectedDocumentId || collabEnabled) {
      return;
    }

    const lastSaved = lastSavedDraftRef.current;
    const draftIsSaved =
      lastSaved.id === selectedDocumentId &&
      lastSaved.title === draftTitle &&
      lastSaved.content === draftContent;

    if (draftIsSaved) {
      setAutoSaveState("saved");
      return;
    }

    setAutoSaveState("pending");
    const timeoutId = window.setTimeout(async () => {
      setAutoSaveState("saving");
      try {
        const data = await api(`/api/documents/${selectedDocumentId}`, {
          method: "PATCH",
          token,
          body: {
            title: draftTitle,
            content: draftContent,
          },
        });
        lastSavedDraftRef.current = {
          id: selectedDocumentId,
          title: data.document.title,
          content: data.document.content,
        };
        setDocuments((current) =>
          current.map((document) => (document.id === selectedDocumentId ? data.document : document)),
        );
        setAutoSaveState("saved");
      } catch (error) {
        setAutoSaveState("error");
        setNotice(error.message);
      }
    }, 900);

    return () => window.clearTimeout(timeoutId);
  }, [collabEnabled, draftContent, draftTitle, selectedDocumentId, token]);

  useEffect(() => {
    if (!collabEnabled || !selectedDocumentId) {
      return;
    }

    const lastSynced = lastSyncedCollabRef.current;
    if (lastSynced.id !== selectedDocumentId || draftContent === lastSynced.content) {
      return;
    }

    setCollabState("pending");
    const timeoutId = window.setTimeout(() => {
      submitCollabDraft(draftContent);
    }, 200);

    return () => window.clearTimeout(timeoutId);
  }, [collabEnabled, collabState, draftContent, selectedDocumentId, token]);

  // 2s interval of collab updates deleted
  // useEffect(() => {
  //   if (!collabEnabled || !selectedDocumentId) {
  //     return;
  //   }

  //   const intervalId = window.setInterval(() => {
  //     pollCollabRevisions();
  //   }, 2000);

  //   return () => window.clearInterval(intervalId);
  // }, [collabEnabled, selectedDocumentId, token]);

  function clearCollabAckTimeout() {
    if (collabAckTimeoutRef.current) {
      window.clearTimeout(collabAckTimeoutRef.current);
      collabAckTimeoutRef.current = null;
    }
  }

  function handleCollabAck(data) {
    clearCollabAckTimeout();
    const pendingContent = pendingCollabSubmitRef.current;
    pendingCollabSubmitRef.current = null;

    lastSyncedCollabRef.current = {
      id: selectedDocumentId,
      content: data.content,
      revision: data.headRevision,
    };
    setCollabRevision(data.headRevision);

    if (pendingContent === null || draftContentRef.current === pendingContent) {
      setDraftContent(data.content);
      setCollabState("live");
    } else {
      setCollabState("pending");
    }

    collabSubmittingRef.current = false;
  }

  function handleCollabSubmitError(error) {
    clearCollabAckTimeout();
    pendingCollabSubmitRef.current = null;
    collabSubmittingRef.current = false;
    setCollabState("error");
    setNotice(error.message);
  }

  useEffect(() => {
    if (!collabEnabled || !selectedDocumentId) {
      return;
    }

    const socket = createCollabSocket(token);
    collabSocketRef.current = socket;

    socket.on("connect", () => {
      socket.emit("join_document", { documentId: selectedDocumentId });
    });

    socket.on("revision_ack", handleCollabAck);

    socket.on("submit_error", handleCollabSubmitError);

    socket.on("revision_applied", (data) => {
      if (data.documentId !== selectedDocumentId) return;

      const lastSynced = lastSyncedCollabRef.current;
      const incoming = data.revision;

      if (incoming.clientId === collabClientId) return;

      if (draftContentRef.current !== lastSynced.content) return;

      lastSyncedCollabRef.current = {
        id: selectedDocumentId,
        content: incoming.contentAfter,
        revision: data.headRevision,
      };

      setDraftContent(incoming.contentAfter);
      setCollabRevision(data.headRevision);
      setCollabState("live");
    });

    socket.on("disconnect", async () => {
      await resyncCollabRevisions();
    });

    return () => {
      clearCollabAckTimeout();
      socket.off("revision_ack", handleCollabAck);
      socket.off("submit_error", handleCollabSubmitError);
      socket.emit("leave_document", { document_id: selectedDocumentId });
      socket.disconnect();
      collabSocketRef.current = null;
    };
  }, [collabEnabled, selectedDocumentId, token, collabClientId]);

  async function resyncCollabRevisions() {
    if (!selectedDocumentId || collabSubmittingRef.current) {
      return;
    }

    const lastSynced = lastSyncedCollabRef.current;

    if (lastSynced.id !== selectedDocumentId) {
      return;
    }

    try {
      const data = await api(
        `/api/documents/${selectedDocumentId}/revisions?since=${lastSynced.revision}`,
        { token }
      );

      if (!data.revisions.length) return;

      const latest = data.revisions[data.revisions.length - 1];
      if (draftContentRef.current !== lastSynced.content) return;

      lastSyncedCollabRef.current = {
        id: selectedDocumentId,
        content: latest.contentAfter,
        revision: data.headRevision,
      };

      setDraftContent(latest.contentAfter);
      setCollabRevision(data.headRevision);
      setCollabState("live");
    } catch (error) {
      setCollabState("error");
      setNotice(error.message);
    }
  }

  async function refreshDocuments(options = {}) {
    if (!options.silent) {
      setStatus("loading");
    }

    try {
      const data = await api("/api/documents", { token });
      setDocuments(data.documents);
      if (!selectedDocumentIdRef.current && data.documents.length) {
        setSelectedDocumentId(data.documents[0].id);
      }
    } catch (error) {
      if (!options.silent) {
        setNotice(error.message);
      }
    } finally {
      if (!options.silent) {
        setStatus("idle");
      }
    }
  }

  async function loadDocument(documentId) {
    try {
      const data = await api(`/api/documents/${documentId}`, { token });
      setDraftTitle(data.document.title);
      setDraftContent(data.document.content);
      lastSavedDraftRef.current = {
        id: documentId,
        title: data.document.title,
        content: data.document.content,
      };
      setAutoSaveState("saved");
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function loadVersions(documentId) {
    try {
      const data = await api(`/api/documents/${documentId}/versions`, { token });
      setVersions(data.versions);
      setDiff(null);
      setIsCompareOpen(false);
      if (data.versions.length >= 2) {
        setToVersionId(String(data.versions[0].id));
        setFromVersionId(String(data.versions[1].id));
      } else {
        setToVersionId(data.versions[0] ? String(data.versions[0].id) : "");
        setFromVersionId("");
      }
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function handleCreateDocument() {
    setStatus("saving");
    setNotice("");
    try {
      const data = await api("/api/documents", {
        method: "POST",
        token,
        body: {
          title: "Untitled document",
          content: "",
        },
      });
      setDocuments((current) => [data.document, ...current]);
      setSelectedDocumentId(data.document.id);
      lastSavedDraftRef.current = {
        id: data.document.id,
        title: data.document.title,
        content: data.document.content,
      };
      setVersions([]);
      setDiff(null);
      setIsCompareOpen(false);
      setNotice("New document ready.");
    } catch (error) {
      setNotice(error.message);
    } finally {
      setStatus("idle");
    }
  }

  async function handleSaveVersion() {
    if (!selectedDocumentId) {
      return;
    }

    setStatus("saving");
    setNotice("");
    try {
      const saved = await api(`/api/documents/${selectedDocumentId}/versions`, {
        method: "POST",
        token,
        body: {
          content: draftContent,
          commitMessage,
        },
      });
      setDocuments((current) =>
        current.map((document) =>
          document.id === selectedDocumentId
            ? {
                ...document,
                content: draftContent,
              }
            : document,
        ),
      );
      lastSavedDraftRef.current = {
        id: selectedDocumentId,
        title: draftTitle,
        content: draftContent,
      };
      setAutoSaveState("saved");
      setCommitMessage("");
      setNotice(saved.summary);
      await loadVersions(selectedDocumentId);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setStatus("idle");
    }
  }

  async function handleDeleteDocument() {
    if (!selectedDocument?.isOwner) {
      return;
    }

    const confirmed = window.confirm(
      `Delete "${selectedDocument.title}"? This also deletes its saved versions and collaboration history.`,
    );
    if (!confirmed) {
      return;
    }

    const documentId = selectedDocument.id;
    setStatus("deleting");
    setNotice("");
    try {
      await api(`/api/documents/${documentId}`, {
        method: "DELETE",
        token,
      });

      const remainingDocuments = documents.filter((document) => document.id !== documentId);
      setDocuments(remainingDocuments);
      setSelectedDocumentId(remainingDocuments[0]?.id ?? null);
      setVersions([]);
      setDraftTitle("");
      setDraftContent("");
      setCommitMessage("");
      setDiff(null);
      setIsCompareOpen(false);
      setFromVersionId("");
      setToVersionId("");
      setCollabEnabled(false);
      lastSavedDraftRef.current = { id: null, title: "", content: "" };
      lastSyncedCollabRef.current = { id: null, content: "", revision: 0 };
      setNotice("Document deleted.");
    } catch (error) {
      setNotice(error.message);
    } finally {
      setStatus("idle");
    }
  }

  async function handleDeleteVersion(version) {
    if (!selectedDocumentId) {
      return;
    }

    const confirmed = window.confirm(
      `Delete Version ${version.versionNumber}? This cannot be undone.`,
    );
    if (!confirmed) {
      return;
    }

    setDeletingVersionId(version.id);
    setNotice("");
    try {
      await api(`/api/documents/${selectedDocumentId}/versions/${version.id}`, {
        method: "DELETE",
        token,
      });
      setDocuments((current) =>
        current.map((document) =>
          document.id === selectedDocumentId
            ? { ...document, versionCount: Math.max(0, (document.versionCount || 1) - 1) }
            : document,
        ),
      );
      setDiff(null);
      setIsCompareOpen(false);
      await loadVersions(selectedDocumentId);
      setNotice(`Deleted Version ${version.versionNumber}.`);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setDeletingVersionId(null);
    }
  }

  async function handleRestoreVersion(version) {
    if (!selectedDocumentId) {
      return;
    }

    setStatus("saving");
    setNotice("");
    try {
      const data = await api(`/api/documents/${selectedDocumentId}/restore`, {
        method: "POST",
        token,
        body: {
          versionId: version.id,
        },
      });
      setDraftTitle(data.document.title);
      setDraftContent(data.document.content);
      setDocuments((current) =>
        current.map((document) => (document.id === selectedDocumentId ? data.document : document)),
      );
      lastSavedDraftRef.current = {
        id: selectedDocumentId,
        title: data.document.title,
        content: data.document.content,
      };
      setAutoSaveState("saved");
      setDiff(null);
      setIsCompareOpen(false);
      setNotice(`Restored version ${data.restoredVersion.versionNumber}.`);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setStatus("idle");
    }
  }

  async function handleToggleCollaboration() {
    if (!selectedDocumentId) {
      return;
    }

    if (collabEnabled) {
      setCollabEnabled(false);
      setCollabState("idle");
      setNotice("Collaboration mode paused.");
      return;
    }

    setCollabState("syncing");
    setNotice("");

    try {
      const state = await api(`/api/documents/${selectedDocumentId}/state`, { token });

      setDraftTitle(state.title);
      setDraftContent(state.content);
      lastSavedDraftRef.current = {
        id: selectedDocumentId,
        title: state.title,
        content: state.content,
      };
      lastSyncedCollabRef.current = {
        id: selectedDocumentId,
        content: state.content,
        revision: state.headRevision,
      };
      setCollabRevision(state.headRevision);
      setAutoSaveState("saved");
      setCollabEnabled(true);
      setCollabState("live");
      setNotice("Collaboration mode is live.");
    } catch (error) {
      setCollabState("error");
      setNotice(error.message);
    }
  }

  async function handleShareDocument(event) {
    event.preventDefault();
    if (!selectedDocumentId || !shareEmail.trim()) {
      return;
    }

    setShareState("sharing");
    setNotice("");

    try {
      const data = await api(`/api/documents/${selectedDocumentId}/share`, {
        method: "POST",
        token,
        body: {
          email: shareEmail,
        },
      });
      setShareEmail("");
      setShareState("idle");
      setNotice(`Shared with ${data.collaborator.email}.`);
    } catch (error) {
      setShareState("error");
      setNotice(error.message);
    }
  }

  async function submitCollabDraftViaHttp(nextContent) {
    const lastSynced = lastSyncedCollabRef.current;

    try {
      const data = await api(`/api/documents/${selectedDocumentId}/revisions`, {
        method: "POST",
        token,
        body: {
          clientId: collabClientId,
          baseRevision: lastSynced.revision,
          changeSet: buildChangeSet(lastSynced.content, nextContent),
        },
      });

      handleCollabAck(data);
    } catch (error) {
      handleCollabSubmitError(error);
    }
  }

  async function submitCollabDraft(nextContent) {
    if (!selectedDocumentId || collabSubmittingRef.current) {
      return;
    }

    const lastSynced = lastSyncedCollabRef.current;
    if (lastSynced.id !== selectedDocumentId || nextContent === lastSynced.content) {
      return;
    }

    const changeSet = buildChangeSet(lastSynced.content, nextContent);
    collabSubmittingRef.current = true;
    pendingCollabSubmitRef.current = nextContent;
    setCollabState("syncing");

    const socket = collabSocketRef.current;
    if (!socket?.connected) {
      await submitCollabDraftViaHttp(nextContent);
      return;
    }

    socket.emit("submit_revision", {
      document_id: selectedDocumentId,
      clientId: collabClientId,
      baseRevision: lastSynced.revision,
      changeSet,
    });

    clearCollabAckTimeout();
    collabAckTimeoutRef.current = window.setTimeout(() => {
      if (!collabSubmittingRef.current) {
        return;
      }

      collabSubmittingRef.current = false;
      pendingCollabSubmitRef.current = null;
      setCollabState("error");
      setNotice("Collaboration sync timed out.");
      resyncCollabRevisions();
    }, 5000);
  }
  // Commenting out old collab code
  // async function pollCollabRevisions() {
  //   if (!selectedDocumentId || collabSubmittingRef.current) {
  //     return;
  //   }

  //   const lastSynced = lastSyncedCollabRef.current;
  //   if (lastSynced.id !== selectedDocumentId) {
  //     return;
  //   }

  //   try {
  //     const data = await api(
  //       `/api/documents/${selectedDocumentId}/revisions?since=${lastSynced.revision}`,
  //       { token },
  //     );

  //     if (!data.revisions.length) {
  //       return;
  //     }

  //     const latest = data.revisions[data.revisions.length - 1];
  //     if (draftContentRef.current !== lastSynced.content) {
  //       return;
  //     }

  //     lastSyncedCollabRef.current = {
  //       id: selectedDocumentId,
  //       content: latest.contentAfter,
  //       revision: data.headRevision,
  //     };
  //     setDraftContent(latest.contentAfter);
  //     setCollabRevision(data.headRevision);
  //     setCollabState("live");
  //   } catch (error) {
  //     setCollabState("error");
  //     setNotice(error.message);
  //   }
  // }

  function handleToggleCompare() {
    const nextOpen = !isCompareOpen;
    setIsCompareOpen(nextOpen);
    if (!nextOpen) {
      setDiff(null);
      return;
    }
    if (versions.length >= 2) {
      setToVersionId(String(versions[0].id));
      setFromVersionId(String(versions[1].id));
    }
  }

  return (
    <main className="workspace-shell">
      <header className="workspace-header">
        <div className="topbar">
          <div className="brand-mark">
            <FileText size={20} aria-hidden="true" />
          </div>
          <span>NotGoogleDocs</span>
        </div>
        <div className="workspace-account">
          <span>{user.email}</span>
          <button className="secondary-action" onClick={onSignOut} type="button">
            Sign out
          </button>
        </div>
      </header>

      <section className="workspace-grid">
        <aside className="document-sidebar" aria-label="Documents">
          <div className="sidebar-head">
            <h2>Documents</h2>
            <button
              aria-label="Create document"
              className="icon-action"
              data-testid="new-document"
              onClick={handleCreateDocument}
              title="Create document"
              type="button"
            >
              <FilePlus size={18} aria-hidden="true" />
            </button>
          </div>
          <div className="document-list">
            {documents.length ? (
              documents.map((document) => (
                <button
                  className={document.id === selectedDocumentId ? "document-item active" : "document-item"}
                  key={document.id}
                  onClick={() => setSelectedDocumentId(document.id)}
                  type="button"
                >
                  <FileText size={16} aria-hidden="true" />
                  <span>
                    <strong>{document.title}</strong>
                    <small>{document.versionCount || 0} saved versions</small>
                  </span>
                </button>
              ))
            ) : (
              <p className="muted">No documents yet.</p>
            )}
          </div>
        </aside>

        <section className="editor-column" aria-label="Document editor">
          {selectedDocument ? (
            <>
              <div className="editor-toolbar">
                <input
                  aria-label="Document title"
                  className="title-input"
                  onChange={(event) => setDraftTitle(event.target.value)}
                  value={draftTitle}
                />
                <div className="toolbar-actions">
                  {selectedDocument.isOwner ? (
                    <button
                      aria-label={`Delete ${selectedDocument.title}`}
                      className="icon-action danger"
                      data-testid="delete-document"
                      disabled={status === "deleting"}
                      onClick={handleDeleteDocument}
                      title="Delete document"
                      type="button"
                    >
                      {status === "deleting" ? (
                        <RefreshCcw className="spinner" size={18} aria-hidden="true" />
                      ) : (
                        <Trash2 size={18} aria-hidden="true" />
                      )}
                    </button>
                  ) : null}
                  <button
                    className={collabEnabled ? "secondary-action collab-toggle active" : "secondary-action collab-toggle"}
                    disabled={!selectedDocumentId || collabState === "syncing"}
                    onClick={handleToggleCollaboration}
                    type="button"
                  >
                    {collabState === "syncing" ? (
                      <RefreshCcw className="spinner" size={18} aria-hidden="true" />
                    ) : (
                      <Users size={18} aria-hidden="true" />
                    )}
                    {collabEnabled ? "Live editing" : "Collaboration"}
                  </button>
                  <button
                    className="primary-action"
                    data-testid="save-version"
                    disabled={!canSaveVersion}
                    onClick={handleSaveVersion}
                    type="button"
                  >
                    {status === "saving" ? (
                      <RefreshCcw className="spinner" size={18} aria-hidden="true" />
                    ) : (
                      <Save size={18} aria-hidden="true" />
                    )}
                    Save version
                  </button>
                </div>
              </div>

              <div className="commit-row">
                <input
                  aria-label="Version note"
                  onChange={(event) => setCommitMessage(event.target.value)}
                  placeholder="Version note, optional"
                  value={commitMessage}
                />
                <span className={`autosave-state ${autoSaveState}`}>{formatAutoSaveState(autoSaveState)}</span>
                {collabEnabled ? (
                  <span className={`collab-state ${collabState}`}>
                    Rev {collabRevision} · {formatCollabState(collabState)}
                  </span>
                ) : null}
                {notice ? <span className="notice">{notice}</span> : null}
              </div>

              {collabEnabled ? (
                <form className="share-row" onSubmit={handleShareDocument}>
                  <label>
                    <span>Share for live editing</span>
                    <input
                      aria-label="Collaborator email"
                      onChange={(event) => setShareEmail(event.target.value)}
                      placeholder="collaborator@example.com"
                      type="email"
                      value={shareEmail}
                    />
                  </label>
                  <button
                    className="secondary-action"
                    disabled={!shareEmail.trim() || shareState === "sharing"}
                    type="submit"
                  >
                    {shareState === "sharing" ? (
                      <RefreshCcw className="spinner" size={18} aria-hidden="true" />
                    ) : (
                      <Users size={18} aria-hidden="true" />
                    )}
                    Share
                  </button>
                </form>
              ) : null}

              <textarea
                aria-label="Document content"
                className="document-editor"
                data-testid="document-content"
                onChange={(event) => setDraftContent(event.target.value)}
                placeholder="Start typing your document..."
                value={draftContent}
              />
            </>
          ) : (
            <div className="empty-workspace">
              <p className="eyebrow">Signed in as {user.email}</p>
              <h1>Your workspace is ready.</h1>
              <button className="primary-action" onClick={handleCreateDocument} type="button">
                <FilePlus size={18} aria-hidden="true" />
                Create document
              </button>
            </div>
          )}
        </section>

        <aside className="history-panel" aria-label="Version history">
          <div className="panel-title">
            <History size={18} aria-hidden="true" />
            <h2>Version history</h2>
          </div>

          <div className="version-list">
            {versions.length ? (
              versions.map((version) => (
                <article className="version-item" key={version.id}>
                  <header className="version-item-head">
                    <div>
                      <strong>Version {version.versionNumber}</strong>
                      <small>
                        <Clock size={13} aria-hidden="true" />
                        {formatDate(version.createdAt)}
                      </small>
                    </div>
                    <span className="version-actions">
                      <button
                        aria-label={`Restore version ${version.versionNumber}`}
                        className="icon-action compact"
                        disabled={status === "saving" || deletingVersionId !== null}
                        onClick={() => handleRestoreVersion(version)}
                        title={`Restore version ${version.versionNumber}`}
                        type="button"
                      >
                        <RotateCcw size={16} aria-hidden="true" />
                      </button>
                      <button
                        aria-label={`Delete version ${version.versionNumber}`}
                        className="icon-action compact danger"
                        disabled={deletingVersionId !== null}
                        onClick={() => handleDeleteVersion(version)}
                        title={`Delete version ${version.versionNumber}`}
                        type="button"
                      >
                        {deletingVersionId === version.id ? (
                          <RefreshCcw className="spinner" size={16} aria-hidden="true" />
                        ) : (
                          <Trash2 size={16} aria-hidden="true" />
                        )}
                      </button>
                    </span>
                  </header>
                  <p>{version.commitMessage || version.summary}</p>
                </article>
              ))
            ) : (
              <p className="muted">Save a version to start history.</p>
            )}
          </div>

          <button
            className="secondary-action compare-toggle"
            disabled={!hasComparableVersions}
            onClick={handleToggleCompare}
            type="button"
          >
            <Split size={18} aria-hidden="true" />
            {isCompareOpen ? "Close compare" : "Compare versions"}
          </button>

          {isCompareOpen ? (
            <div className="compare-controls">
              <label>
                <span>From</span>
                <select
                  disabled={!hasComparableVersions}
                  onChange={(event) => setFromVersionId(event.target.value)}
                  value={fromVersionId}
                >
                  <option value="">Choose</option>
                  {versions.map((version) => (
                    <option key={version.id} value={version.id}>
                      Version {version.versionNumber}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>To</span>
                <select
                  disabled={!hasComparableVersions}
                  onChange={(event) => setToVersionId(event.target.value)}
                  value={toVersionId}
                >
                  <option value="">Choose</option>
                  {versions.map((version) => (
                    <option key={version.id} value={version.id}>
                      Version {version.versionNumber}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          ) : null}
        </aside>
      </section>

      {isCompareOpen ? (
        <section className="diff-panel" aria-label="Split diff viewer">
          <div className="panel-title">
            <FileDiff size={18} aria-hidden="true" />
            <h2>Split diff</h2>
          </div>
          {diff ? (
            <>
              <p className="diff-summary">{diff.summary}</p>
              <div className="diff-grid">
                <div className="diff-pane">
                  <header>Version {diff.from.versionNumber}</header>
                  <DiffText chunks={diff.chunks} side="left" />
                </div>
                <div className="diff-pane">
                  <header>Version {diff.to.versionNumber}</header>
                  <DiffText chunks={diff.chunks} side="right" />
                </div>
              </div>
            </>
          ) : (
            <p className="muted">Choose two saved versions to compare changes.</p>
          )}
        </section>
      ) : null}
    </main>
  );
}

function DiffText({ chunks, side }) {
  return (
    <pre className="diff-text">
      {chunks.map((chunk, index) => {
        const text = side === "left" ? chunk.left : chunk.right;
        if (!text) {
          return null;
        }

        let className = "diff-equal";
        if (side === "left" && (chunk.type === "delete" || chunk.type === "replace")) {
          className = "diff-delete";
        }
        if (side === "right" && (chunk.type === "insert" || chunk.type === "replace")) {
          className = "diff-insert";
        }

        return (
          <span className={className} key={`${side}-${index}`}>
            {text}
          </span>
        );
      })}
    </pre>
  );
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatAutoSaveState(state) {
  if (state === "saving") {
    return "Saving draft...";
  }
  if (state === "pending") {
    return "Draft changes pending";
  }
  if (state === "error") {
    return "Draft not saved";
  }
  if (state === "saved") {
    return "Draft saved";
  }
  return "";
}

function formatCollabState(state) {
  if (state === "syncing") {
    return "Syncing";
  }
  if (state === "pending") {
    return "Local edit pending";
  }
  if (state === "error") {
    return "Sync issue";
  }
  return "Live";
}

function getOrCreateClientId() {
  const existing = sessionStorage.getItem(clientIdKey);
  if (existing) {
    return existing;
  }

  const next = `client-${Math.random().toString(36).slice(2, 10)}`;
  sessionStorage.setItem(clientIdKey, next);
  return next;
}

function buildChangeSet(oldText, newText) {
  let prefixLength = 0;
  while (
    prefixLength < oldText.length &&
    prefixLength < newText.length &&
    oldText[prefixLength] === newText[prefixLength]
  ) {
    prefixLength += 1;
  }

  let suffixLength = 0;
  while (
    suffixLength + prefixLength < oldText.length &&
    suffixLength + prefixLength < newText.length &&
    oldText[oldText.length - 1 - suffixLength] === newText[newText.length - 1 - suffixLength]
  ) {
    suffixLength += 1;
  }

  const deleteCount = oldText.length - prefixLength - suffixLength;
  const insertText = newText.slice(prefixLength, newText.length - suffixLength);
  const ops = [];

  if (prefixLength > 0) {
    ops.push({ type: "retain", count: prefixLength });
  }
  if (deleteCount > 0) {
    ops.push({ type: "delete", count: deleteCount });
  }
  if (insertText) {
    ops.push({ type: "insert", text: insertText });
  }
  if (suffixLength > 0) {
    ops.push({ type: "retain", count: suffixLength });
  }

  return {
    baseLength: oldText.length,
    ops,
  };
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
  };

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || `Request failed with status ${response.status}.`);
  }

  return data;
}

createRoot(document.getElementById("root")).render(<App />);
