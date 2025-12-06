// Full updated script.js — server-backed per-user chats (no shared localStorage)

document.addEventListener("DOMContentLoaded", () => {
  // === Data in memory (server-backed) ===
  let chats = {}; // active
  let archivedChats = {};
  let meta = {};
  let currentChat = "Chat 1";

  // === DOM refs ===
  const chatsListEl = document.getElementById("chats");
  const archivedListEl = document.getElementById("archived-list");
  const newChatBtn = document.getElementById("new-chat");
  const newAIChatBtn = document.getElementById("new-ai-chat");
  const messagesEl = document.getElementById("messages");
  const titleEl = document.getElementById("current-chat-title");
  const inputEl = document.getElementById("message-input");
  const sendBtn = document.getElementById("send-btn");
  const appEl = document.getElementById("app");

  // dialogs and controls
  const settingsDialog = document.getElementById("settings-dialog");
  const settingsOpen = document.getElementById("settings-open");
  const settingsClose = document.getElementById("settings-close");
  const darkBtn = document.getElementById("dark-btn");
  const lightBtn = document.getElementById("light-btn");
  const sidebarToggleBtn = document.getElementById("sidebar-toggle-btn");
  const deleteAllChatsBtn = document.getElementById("delete-all-chats");
  const logoutBtn = document.getElementById("logout-btn");
  const archiveOpenBtn = document.getElementById("archive-open");
  const archiveDialog = document.getElementById("archive-dialog");

  const guidelinesOpen = document.getElementById("guidelines-open");
  const howtoOpen = document.getElementById("howto-open");

  const renameDialog = document.getElementById("rename-dialog");
  const renameInput = document.getElementById("rename-input");
  const renameConfirm = document.getElementById("rename-confirm");
  const renameClose = document.getElementById("rename-cancel");

  const deleteDialog = document.getElementById("delete-dialog");
  const deleteConfirm = document.getElementById("delete-confirm");
  const deleteCancelAction = document.getElementById("delete-cancel-action");

  const algebraOptionsDialog = document.getElementById("algebra-options");
  const algebraClose = document.getElementById("algebra-close");
  const optSimplify = document.getElementById("opt-simplify");
  const optSolve = document.getElementById("opt-solve");

  // generic dialogs
  const notifyDialog = document.getElementById("notify-dialog");
  const notifyTitle = document.getElementById("notify-title");
  const notifyMessage = document.getElementById("notify-message");
  const notifyOk = document.getElementById("notify-ok");

  const confirmDialog = document.getElementById("confirm-dialog");
  const confirmYes = confirmDialog ? confirmDialog.querySelector(".confirm-yes") : null;
  const confirmNo = confirmDialog ? confirmDialog.querySelector(".confirm-no") : null;
  const confirmMessageEl = confirmDialog ? confirmDialog.querySelector(".confirm-message") : null;

  const promptDialog = document.getElementById("prompt-dialog");
  const promptTitle = document.getElementById("prompt-title");
  const promptInput = document.getElementById("prompt-input");
  const promptOk = document.getElementById("prompt-ok");
  const promptCancel = document.getElementById("prompt-cancel");

  const editMessageDialog = document.getElementById("edit-message-dialog");
  const editMessageInput = document.getElementById("edit-message-input");
  const editMessageSave = document.getElementById("edit-message-save");
  const editMessageCancel = document.getElementById("edit-message-cancel");

  // === Helpers ===
  async function fetchUserChats() {
    try {
      const resp = await fetch('/api/chats');
      if (resp.status === 401) {
        // not authenticated — redirect to login
        window.location.href = '/login';
        return null;
      }
      const data = await resp.json();
      return data;
    } catch (err) {
      await showNotification("Network error while loading chats: " + (err.message || err), "Error");
      return null;
    }
  }

  async function saveChats() {
    // send active, archived, meta to server
    try {
      const resp = await fetch('/api/chats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: chats, archived: archivedChats, meta: meta })
      });
      if (resp.status === 401) {
        await showNotification("Session expired. Redirecting to login.", "Authentication");
        window.location.href = '/login';
        return;
      }
      // ignore body for now
    } catch (err) {
      // show a non-blocking notification
      console.warn("Failed to save chats to server:", err);
    }
  }

  // === Dialog helper functions (promise-based) ===
  function showNotification(message, title = "Message") {
    return new Promise(resolve => {
      if (!notifyDialog) { alert(message); resolve(); return; }
      notifyTitle.textContent = title;
      notifyMessage.innerHTML = message;
      function closeHandler() {
        notifyOk.removeEventListener("click", closeHandler);
        notifyDialog.close();
        resolve();
      }
      notifyOk.addEventListener("click", closeHandler);
      notifyDialog.showModal();
    });
  }

  function showConfirm(message) {
    return new Promise(resolve => {
      if (!confirmDialog) { resolve(window.confirm(message)); return; }
      confirmMessageEl.innerHTML = message;
      function yes() { cleanup(); resolve(true); }
      function no() { cleanup(); resolve(false); }
      function cleanup() {
        confirmYes.removeEventListener("click", yes);
        confirmNo.removeEventListener("click", no);
        confirmDialog.close();
      }
      confirmYes.addEventListener("click", yes);
      confirmNo.addEventListener("click", no);
      confirmDialog.showModal();
    });
  }

  function showPrompt(title = "Input", placeholder = "", defaultValue = "") {
    return new Promise(resolve => {
      if (!promptDialog) { const r = window.prompt(title, defaultValue); resolve(r); return; }
      promptTitle.textContent = title;
      promptInput.value = defaultValue || "";
      promptInput.placeholder = placeholder || "";
      function ok() { cleanup(); resolve(promptInput.value); }
      function cancel() { cleanup(); resolve(null); }
      function cleanup() {
        promptOk.removeEventListener("click", ok);
        promptCancel.removeEventListener("click", cancel);
        promptDialog.close();
      }
      promptOk.addEventListener("click", ok);
      promptCancel.addEventListener("click", cancel);
      promptDialog.showModal();
      setTimeout(() => promptInput.focus(), 50);
    });
  }

  function showEditMessage(currentText) {
    return new Promise(resolve => {
      if (!editMessageDialog) { const val = window.prompt("Edit message:", currentText); resolve(val); return; }
      editMessageInput.value = currentText || "";
      function save() { cleanup(); resolve(editMessageInput.value); }
      function cancel() { cleanup(); resolve(null); }
      function cleanup() {
        editMessageSave.removeEventListener("click", save);
        editMessageCancel.removeEventListener("click", cancel);
        editMessageDialog.close();
      }
      editMessageSave.addEventListener("click", save);
      editMessageCancel.addEventListener("click", cancel);
      editMessageDialog.showModal();
      setTimeout(() => editMessageInput.focus(), 50);
    });
  }

  // Close-x buttons behavior
  document.querySelectorAll('button.close-x').forEach(btn => {
    const closeId = btn.getAttribute('data-close');
    if (!closeId) return;
    btn.addEventListener('click', () => {
      const dlg = document.getElementById(closeId);
      if (dlg && typeof dlg.close === 'function') dlg.close();
    });
  });

  // === Sidebar & theme ===
  const STORAGE_KEY_SIDEBAR = "math_helper_sidebar_state_v2";
  function loadSidebarState() {
    const isClosed = localStorage.getItem(STORAGE_KEY_SIDEBAR) === 'closed';
    if (isClosed) appEl.classList.add('sidebar-closed'); else appEl.classList.remove('sidebar-closed');
  }
  function toggleSidebar() {
    const isClosed = appEl.classList.toggle('sidebar-closed');
    localStorage.setItem(STORAGE_KEY_SIDEBAR, isClosed ? 'closed' : 'open');
  }
  if (sidebarToggleBtn) sidebarToggleBtn.addEventListener('click', toggleSidebar);
  if (darkBtn) darkBtn.addEventListener('click', () => { document.body.classList.add("theme-dark"); localStorage.setItem("math_helper_theme","dark"); });
  if (lightBtn) lightBtn.addEventListener('click', () => { document.body.classList.remove("theme-dark"); localStorage.setItem("math_helper_theme","light");});

  // Add logout button handler (redirects to /logout)
  if (logoutBtn) logoutBtn.addEventListener('click', () => {
    window.location.href = '/logout';
  });

  // === Event wiring for settings/guides/archive ===
  if (settingsOpen) settingsOpen.addEventListener('click', () => settingsDialog.showModal());
  if (settingsClose) settingsClose.addEventListener('click', () => settingsDialog.close());
  if (guidelinesOpen) guidelinesOpen.addEventListener('click', () => document.getElementById('guidelines-dialog').showModal());
  if (howtoOpen) howtoOpen.addEventListener('click', () => document.getElementById('howto-dialog').showModal());
  if (archiveOpenBtn) archiveOpenBtn.addEventListener('click', () => { renderArchivedList(); archiveDialog.showModal(); });

  // === Chat list rendering & actions ===
  function createChatItem(name, list, isActive, actionsType) {
    const item = document.createElement("div");
    item.className = "chat-item" + (isActive ? " active" : "");
    const spanName = document.createElement("div");
    spanName.className = "name";
    spanName.textContent = name + (meta[name] && meta[name].ai ? " (AI)" : "");
    spanName.onclick = () => { if (actionsType==='active') { currentChat = name; renderMessages(); renderChatList(); } };
    const actions = document.createElement("div");
    actions.className = "actions";

    if (actionsType === 'active') {
      const pencil = document.createElement("button"); pencil.innerHTML="✏️"; pencil.title="Rename";
      pencil.addEventListener('click', (e) => { e.stopPropagation(); openRenameDialog(name); }); actions.append(pencil);

      const archive = document.createElement("button"); archive.innerHTML="📦"; archive.title="Archive";
      archive.addEventListener('click', (e) => { e.stopPropagation(); archiveChat(name); }); actions.append(archive);
    } else {
      const unarchive = document.createElement("button"); unarchive.innerHTML="↩️"; unarchive.title="Unarchive";
      unarchive.addEventListener('click', (e)=>{ e.stopPropagation(); unarchiveChat(name);}); actions.append(unarchive);
    }

    const bin = document.createElement("button"); bin.innerHTML="🗑️"; bin.title="Delete";
    bin.addEventListener('click', (e)=>{ e.stopPropagation(); openDeleteDialog(name, actionsType); }); actions.append(bin);

    item.append(spanName, actions);
    list.appendChild(item);
  }

  function renderChatList() {
    if (!chatsListEl) return;
    chatsListEl.innerHTML = "";
    Object.keys(chats).forEach(name => createChatItem(name, chatsListEl, name===currentChat, 'active'));
  }

  function renderArchivedList() {
    if (!archivedListEl) return;
    archivedListEl.innerHTML = "";
    Object.keys(archivedChats).forEach(name => createChatItem(name, archivedListEl, false, 'archived'));
  }

  // === Messages rendering ===
  function renderMessages() {
    if (!messagesEl || !titleEl) return;
    titleEl.textContent = currentChat + (meta[currentChat] && meta[currentChat].ai ? " (AI)" : "");
    messagesEl.innerHTML = "";
    const list = chats[currentChat];
    if (!list) { currentChat = Object.keys(chats)[0] || "Chat 1"; return renderMessages(); }
    list.forEach((msg, idx) => {
      appendMessage(msg.user, "user", idx);
      appendMessage(msg.bot, "bot", idx);
    });
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function appendMessage(text, sender, index) {
    const row = document.createElement("div"); row.className = "message-row " + sender;
    const bubble = document.createElement("div"); bubble.className = "bubble " + sender;
    if (sender === "bot") bubble.innerHTML = text;
    else bubble.textContent = text;
    if (sender === "user") bubble.ondblclick = ()=> openEditMessage(index);
    row.appendChild(bubble); messagesEl.appendChild(row);
  }

  // === Sending messages / AI interactions ===
  async function requestAiReply(chatName, historyArray) {
    const msgs = [];
    const systemText = "You are a precise math tutor. When given arithmetic or algebra, produce a clear, correct solution and steps. Respond only with the assistant's content (no JSON) when used as assistant. The client expects plain text or simple HTML (<strong>, <br>, <code>).";
    msgs.push({ role: "system", content: [{ type: "text", text: systemText }] });

    for (const turn of historyArray) {
      if (turn.user && turn.user.trim()) {
        msgs.push({ role: "user", content: [{ type: "text", text: String(turn.user) }] });
      }
      if (turn.bot && turn.bot.trim()) {
        msgs.push({ role: "assistant", content: [{ type: "text", text: String(turn.bot) }] });
      }
    }

    const resp = await fetch("/ai_reply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_name: chatName, messages: msgs })
    });

    if (resp.status === 401) {
      await showNotification("Session expired or authentication required. Redirecting to login.", "Authentication");
      window.location.href = '/login';
      return null;
    }
    const data = await resp.json();
    return data;
  }

  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = "";

    // push user message into local chat (memory)
    if (!chats[currentChat]) chats[currentChat] = [];
    chats[currentChat].push({ user: text, bot: "" });
    saveChats(); renderMessages();

    if (meta[currentChat] && meta[currentChat].ai) {
      const history = chats[currentChat].map(m => ({ user: m.user, bot: m.bot }));
      try {
        const result = await requestAiReply(currentChat, history);
        if (!result) return;
        if (result.error) {
          const last = chats[currentChat][chats[currentChat].length - 1];
          last.bot = `AI error: ${result.error}`;
          saveChats(); renderMessages();
          await showNotification("AI error: " + result.error, "AI Error");
          return;
        }
        const last = chats[currentChat][chats[currentChat].length - 1];
        last.bot = result.reply || "(no reply)";
        saveChats(); renderMessages();
      } catch (err) {
        const last = chats[currentChat][chats[currentChat].length - 1];
        last.bot = `Error communicating with AI: ${err.message || String(err)}`;
        saveChats(); renderMessages();
        await showNotification("Error communicating with AI: " + (err.message || String(err)), "Network Error");
      }
    } else {
      try {
        const resp = await fetch("/send", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text })
        });
        if (resp.status === 401) {
          await showNotification("Session expired or authentication required. Redirecting to login.", "Authentication");
          window.location.href = '/login';
          return;
        }
        const data = await resp.json();
        const last = chats[currentChat][chats[currentChat].length - 1];
        last.bot = data.reply || "(no reply)";
        saveChats(); renderMessages();
      } catch (err) {
        const last = chats[currentChat][chats[currentChat].length - 1];
        last.bot = `Error communicating with the server: ${err.message}`;
        saveChats(); renderMessages();
        await showNotification("Error: " + (err.message || String(err)), "Network Error");
      }
    }
  }

  // send on click or Enter
  if (sendBtn) sendBtn.addEventListener('click', sendMessage);
  if (inputEl) inputEl.addEventListener('keydown', e => { if (e.key === "Enter") { e.preventDefault(); sendMessage(); } });

  // === New AI Chat creation ===
  if (newAIChatBtn) newAIChatBtn.addEventListener('click', async () => {
    const topic = await showPrompt("Optional topic", "e.g. basic algebra, hcf examples", "");
    newAIChatBtn.disabled = true;
    const prevText = newAIChatBtn.textContent;
    newAIChatBtn.textContent = "⏳ Generating...";
    try {
      const res = await fetch("/new_ai_chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic || "" })
      });
      if (res.status === 401) {
        await showNotification("Session expired or authentication required. Redirecting to login.", "Authentication");
        window.location.href = '/login';
        return;
      }

      // parse JSON if possible
      let data = null;
      try { data = await res.json(); } catch (e) { data = null; }

      if (!res.ok) {
        // show server-provided error message when available
        const errMsg = data && data.error ? data.error : `Server error: ${res.status} ${res.statusText}`;
        await showNotification("AI error: " + errMsg, "Error");
        return;
      }

      if (!data || !data.chat_name || !Array.isArray(data.messages)) {
        await showNotification("Failed to create AI chat. Server returned unexpected data.", "Error");
        return;
      }
      let name = data.chat_name;
      let finalName = name; let i = 1;
      while (chats[finalName] || archivedChats[finalName]) { i += 1; finalName = `${name} (${i})`; }

      chats[finalName] = data.messages.map(m => ({ user: String(m.user||""), bot: String(m.bot||"") }));
      meta[finalName] = { ai: true };
      currentChat = finalName;
      saveChats(); renderChatList(); renderMessages();
      await showNotification(`Created AI chat: "${finalName}"`, "AI Chat Created");
    } catch (err) {
      await showNotification("Error creating AI chat: " + (err.message || String(err)), "Error");
    } finally {
      newAIChatBtn.disabled = false;
      newAIChatBtn.textContent = prevText;
    }
  });

  // === New regular chat ===
  if (newChatBtn) newChatBtn.addEventListener('click', () => {
    let i = 1; while (chats[`Chat ${i}`] || archivedChats[`Chat ${i}`]) i++;
    const name = `Chat ${i}`; chats[name] = []; currentChat = name; saveChats(); renderChatList(); renderMessages();
  });

  // === Delete all (active) ===
  if (deleteAllChatsBtn) deleteAllChatsBtn.addEventListener('click', async () => {
    const ok = await showConfirm("Are you sure you want to delete ALL active chats? Archived chats will remain.");
    if (!ok) return;
    chats = {}; chats["Chat 1"] = []; meta = {}; currentChat = "Chat 1"; saveChats(); renderChatList(); renderMessages();
  });

  // === Rename ===
  function openRenameDialog(name) {
    renameDialog.dataset.chat = name; renameInput.value = name; renameDialog.showModal();
  }
  if (renameConfirm) renameConfirm.addEventListener('click', async () => {
    const oldName = renameDialog.dataset.chat; const newName = renameInput.value.trim();
    if (!newName || chats[newName] || archivedChats[newName]) { await showNotification("Chat name invalid or duplicate.", "Rename Error"); return; }
    if (chats[oldName]) { chats[newName] = chats[oldName]; delete chats[oldName]; if (meta[oldName]) { meta[newName] = meta[oldName]; delete meta[oldName]; } currentChat = newName; renderMessages(); }
    else if (archivedChats[oldName]) { archivedChats[newName] = archivedChats[oldName]; delete archivedChats[oldName]; }
    saveChats(); renderChatList(); renameDialog.close();
  });
  if (renameClose) renameClose.addEventListener('click', ()=> renameDialog.close());

  // === Archive / Unarchive ===
  function archiveChat(name) {
    archivedChats[name] = chats[name]; delete chats[name];
    if (meta[name]) { archivedChats[name + ".__meta__"] = meta[name]; delete meta[name]; }
    if (name === currentChat) currentChat = Object.keys(chats)[0] || "Chat 1";
    saveChats(); renderChatList();
  }
  async function unarchiveChat(name) {
    if (chats[name]) { await showNotification("Active chat with same name exists. Rename first.", "Unarchive"); return; }
    chats[name] = archivedChats[name]; delete archivedChats[name];
    if (archivedChats[name + ".__meta__"]) { meta[name] = archivedChats[name + ".__meta__"]; delete archivedChats[name + ".__meta__"]; }
    saveChats(); renderChatList(); renderArchivedList(); currentChat = name; renderMessages(); archiveDialog.close();
  }

  // === Delete chat ===
  function openDeleteDialog(name, listType) { deleteDialog.dataset.chat = name; deleteDialog.dataset.list = listType; deleteDialog.showModal(); }
  if (deleteConfirm) deleteConfirm.addEventListener('click', () => {
    const name = deleteDialog.dataset.chat; const listType = deleteDialog.dataset.list;
    if (listType === 'active') { delete chats[name]; if (meta[name]) delete meta[name]; if (name === currentChat) currentChat = Object.keys(chats)[0] || "Chat 1"; renderMessages(); renderChatList(); }
    else if (listType === 'archived') { delete archivedChats[name]; delete archivedChats[name + ".__meta__"]; renderArchivedList(); }
    saveChats(); deleteDialog.close();
  });
  if (deleteCancelAction) deleteCancelAction.addEventListener('click', ()=> deleteDialog.close());

  // === Edit user message ===
  async function openEditMessage(index) {
    const msg = chats[currentChat][index];
    const newText = await showEditMessage(msg.user);
    if (newText === null) return;
    msg.user = newText; msg.bot = "(edited — resend to update)"; saveChats(); renderMessages();
  }

  // === Algebra options dialog actions ===
  if (optSimplify) optSimplify.addEventListener('click', () => { const expr = algebraOptionsDialog.dataset.expr; algebraOptionsDialog.close(); inputEl.value = `simplify ${expr}`; sendMessage(); });
  if (optSolve) optSolve.addEventListener('click', () => { const expr = algebraOptionsDialog.dataset.expr; algebraOptionsDialog.close(); inputEl.value = `solve ${expr}`; sendMessage(); });

  // === Archived list rendering helper referenced earlier ===
  function renderArchivedList() {
    if (!archivedListEl) return;
    archivedListEl.innerHTML = "";
    Object.keys(archivedChats).forEach(name => {
      if (name.endsWith(".__meta__")) return;
      createChatItem(name, archivedListEl, false, 'archived');
    });
  }

  // Load saved sidebar state
  loadSidebarState();

  // === Initialization: load chats from server ===
  (async function init() {
    const data = await fetchUserChats();
    if (!data) return;
    chats = data.active || { "Chat 1": [] };
    archivedChats = data.archived || {};
    meta = data.meta || {};
    // ensure at least one chat exists
    if (Object.keys(chats).length === 0) chats["Chat 1"] = [];
    currentChat = Object.keys(chats)[0] || "Chat 1";
    renderChatList();
    renderMessages();
  })();

}); // DOMContentLoaded