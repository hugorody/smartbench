(function () {
  async function switchWorkspace(workspaceId) {
    if (!workspaceId) return;
    await fetch(`/api/workspaces/switch/${workspaceId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    window.location.reload();
  }

  function bindWorkspaceSwitcher() {
    const switcher = document.getElementById("workspace-switcher");
    if (!switcher) return;
    if (switcher.dataset.bound === "true") return;
    switcher.dataset.bound = "true";
    switcher.addEventListener("change", (event) => {
      switchWorkspace(event.target.value);
    });
  }

  function bindContextFilters() {
    document.querySelectorAll("input[data-filter-input]").forEach((input) => {
      if (input.dataset.bound === "true") return;
      input.dataset.bound = "true";
      const targetId = input.getAttribute("data-filter-input");
      const target = document.getElementById(targetId);
      if (!target) return;

      input.addEventListener("input", () => {
        const query = input.value.trim().toLowerCase();
        target.querySelectorAll(".filter-item").forEach((item) => {
          const visible = !query || item.textContent.toLowerCase().includes(query);
          item.classList.toggle("hidden", !visible);
        });
      });
    });
  }

  function bindContextSelection() {
    document.querySelectorAll("[data-context-list] a[data-context-item]").forEach((link) => {
      if (link.dataset.bound === "true") return;
      link.dataset.bound = "true";
      link.addEventListener("click", () => {
        const list = link.closest("[data-context-list]");
        if (!list) return;

        list.querySelectorAll("a[data-context-item]").forEach((item) => {
          item.classList.remove("border-shell-300", "bg-shell-100");
          item.classList.add("border-slate-200", "bg-white");
        });

        link.classList.remove("border-slate-200", "bg-white");
        link.classList.add("border-shell-300", "bg-shell-100");
      });
    });
  }

  function applyContextPanelState(panelWrapper, showButton) {
    const collapsed = panelWrapper.dataset.contextCollapsed === "true";
    const isDesktop = window.matchMedia("(min-width: 1024px)").matches;

    panelWrapper.classList.add("hidden");
    if (collapsed) {
      panelWrapper.classList.remove("lg:flex");
      panelWrapper.classList.add("lg:hidden");
    } else {
      panelWrapper.classList.remove("lg:hidden");
      panelWrapper.classList.add("lg:flex");
    }

    showButton.style.display = collapsed && isDesktop ? "inline-flex" : "none";
  }

  function bindContextPanelToggle() {
    const panelWrapper = document.getElementById("context-panel-wrapper");
    const hideButton = document.getElementById("context-panel-hide-btn");
    const showButton = document.getElementById("context-panel-show-btn");
    if (!panelWrapper || !hideButton || !showButton) return;

    if (panelWrapper.dataset.contextToggleBound !== "true") {
      panelWrapper.dataset.contextToggleBound = "true";
      panelWrapper.dataset.contextCollapsed = panelWrapper.dataset.contextCollapsed || "false";

      hideButton.addEventListener("click", () => {
        panelWrapper.dataset.contextCollapsed = "true";
        applyContextPanelState(panelWrapper, showButton);
      });

      showButton.addEventListener("click", () => {
        panelWrapper.dataset.contextCollapsed = "false";
        applyContextPanelState(panelWrapper, showButton);
      });

      window.addEventListener("resize", () => {
        applyContextPanelState(panelWrapper, showButton);
      });
    }

    applyContextPanelState(panelWrapper, showButton);
  }

  function toggleContextPanel() {
    const panelWrapper = document.getElementById("context-panel-wrapper");
    const hideButton = document.getElementById("context-panel-hide-btn");
    const showButton = document.getElementById("context-panel-show-btn");
    if (!panelWrapper || !hideButton || !showButton) return;

    const collapsed = panelWrapper.dataset.contextCollapsed === "true";
    if (collapsed) {
      showButton.click();
      return;
    }
    hideButton.click();
  }

  function bindHtmxProgress() {
    const progress = document.getElementById("htmx-progress");
    if (!progress) return;
    if (document.body.dataset.htmxProgressBound === "true") return;
    document.body.dataset.htmxProgressBound = "true";

    let pendingRequests = 0;
    let settleTimer = null;

    const begin = () => {
      pendingRequests += 1;
      if (settleTimer) {
        window.clearTimeout(settleTimer);
        settleTimer = null;
      }
      progress.style.transform = "";
      progress.classList.add("is-loading");
    };

    const end = () => {
      pendingRequests = Math.max(0, pendingRequests - 1);
      if (pendingRequests > 0) return;

      progress.style.transform = "scaleX(1)";
      settleTimer = window.setTimeout(() => {
        progress.classList.remove("is-loading");
        progress.style.transform = "";
      }, 220);
    };

    document.body.addEventListener("htmx:beforeRequest", begin);
    document.body.addEventListener("htmx:afterRequest", end);
    document.body.addEventListener("htmx:responseError", end);
    document.body.addEventListener("htmx:sendError", end);
    document.body.addEventListener("htmx:timeout", end);
  }

  function bindQuickActions() {
    const modal = document.getElementById("quick-actions-modal");
    const openButton = document.getElementById("quick-actions-open-btn");
    const backdrop = document.getElementById("quick-actions-backdrop");
    const input = document.getElementById("quick-actions-input");
    const commandList = document.getElementById("quick-actions-list");
    if (!modal || !openButton || !backdrop || !input || !commandList) return;
    if (modal.dataset.bound === "true") return;
    modal.dataset.bound = "true";

    const commandItems = Array.from(commandList.querySelectorAll("[data-command-item]"));

    const visibleCommands = () => commandItems.filter((item) => !item.classList.contains("hidden"));

    const filterCommands = (query) => {
      const normalized = query.trim().toLowerCase();
      commandItems.forEach((item) => {
        const visible = !normalized || item.textContent.toLowerCase().includes(normalized);
        item.classList.toggle("hidden", !visible);
      });
    };

    const openModal = () => {
      modal.classList.remove("hidden");
      openButton.setAttribute("aria-expanded", "true");
      input.value = "";
      filterCommands("");
      window.setTimeout(() => {
        input.focus();
      }, 0);
    };

    const closeModal = () => {
      modal.classList.add("hidden");
      openButton.setAttribute("aria-expanded", "false");
      openButton.focus();
    };

    openButton.addEventListener("click", openModal);
    backdrop.addEventListener("click", closeModal);

    input.addEventListener("input", () => {
      filterCommands(input.value);
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        const first = visibleCommands()[0];
        if (first) {
          window.location.assign(first.getAttribute("href") || "#");
        }
      }
      if (event.key === "Escape") {
        closeModal();
      }
    });

    commandItems.forEach((item) => {
      item.addEventListener("click", () => {
        closeModal();
      });
    });

    document.addEventListener("keydown", (event) => {
      const key = event.key.toLowerCase();
      const isMetaCombo = event.metaKey || event.ctrlKey;

      if (isMetaCombo && key === "k") {
        event.preventDefault();
        if (modal.classList.contains("hidden")) {
          openModal();
        } else {
          closeModal();
        }
        return;
      }

      if (isMetaCombo && key === "b") {
        event.preventDefault();
        toggleContextPanel();
        return;
      }

      if (event.key === "Escape" && !modal.classList.contains("hidden")) {
        event.preventDefault();
        closeModal();
      }
    });
  }

  function escapeHtml(value) {
    return value
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function conversationStorageKey(sessionId) {
    return `smartbench_agent_thread_${sessionId}`;
  }

  function readConversationHistory(sessionId) {
    if (!sessionId) return [];
    try {
      const raw = window.localStorage.getItem(conversationStorageKey(sessionId));
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function writeConversationHistory(sessionId, history) {
    if (!sessionId) return;
    try {
      window.localStorage.setItem(conversationStorageKey(sessionId), JSON.stringify(history));
    } catch {
      // Ignore browser storage quota failures.
    }
  }

  function appendConversationEntry(sessionId, entry) {
    const history = readConversationHistory(sessionId);
    history.push(entry);
    writeConversationHistory(sessionId, history);
  }

  function appendAgentMessage(role, content, actions, options = {}) {
    const { persist = false, sessionId = null } = options;
    const messageList = document.getElementById("agent-message-list");
    if (!messageList) return;

    const isUser = role === "user";
    const wrapper = document.createElement("article");
    wrapper.className = `flex ${isUser ? "justify-end" : "justify-start"}`;

    let actionsHtml = "";
    if (!isUser && Array.isArray(actions) && actions.length > 0) {
      const rows = actions
        .map((action) => {
          const name = escapeHtml(action.tool_name || "tool");
          const status = escapeHtml(action.status || "unknown");
          return `<li class=\"rounded border border-slate-200 bg-white p-2\"><p class=\"font-mono text-[11px] text-slate-800\">${name}</p><p class=\"mt-1 text-[11px] text-slate-600\">status: ${status}</p></li>`;
        })
        .join("");
      actionsHtml = `<div class=\"mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-700\"><p class=\"font-semibold text-slate-800\">Tool Actions</p><ul class=\"mt-2 space-y-2\">${rows}</ul></div>`;
    }

    wrapper.innerHTML = `
      <div class=\"max-w-3xl rounded-2xl px-4 py-3 shadow-panel ${
        isUser ? "bg-shell-900 text-white" : "border border-slate-200 bg-white text-slate-900"
      }\">
        <p class=\"whitespace-pre-wrap text-sm leading-relaxed\">${escapeHtml(content)}</p>
        ${actionsHtml}
      </div>
    `;

    messageList.appendChild(wrapper);
    wrapper.scrollIntoView({ behavior: "smooth", block: "end" });

    if (persist && sessionId) {
      appendConversationEntry(sessionId, { role, content, actions: actions || [] });
    }
  }

  function hydrateConversationFromStorage(sessionId) {
    const messageList = document.getElementById("agent-message-list");
    if (!messageList || !sessionId) return;
    if (messageList.dataset.hydrated === "true") return;
    messageList.dataset.hydrated = "true";

    const serverCount = Number(messageList.dataset.serverMessageCount || "0");
    if (serverCount > 0) {
      return;
    }

    const history = readConversationHistory(sessionId);
    history.forEach((entry) => {
      appendAgentMessage(entry.role || "assistant", entry.content || "", entry.actions || [], {
        persist: false,
        sessionId,
      });
    });
  }

  function bindAgentSessionDeleteForms() {
    document.querySelectorAll("form[data-agent-delete-form]").forEach((form) => {
      if (form.dataset.bound === "true") return;
      form.dataset.bound = "true";
      form.addEventListener("submit", (event) => {
        const sessionId = form.dataset.sessionId || "";
        const ok = window.confirm("Delete this conversation?");
        if (!ok) {
          event.preventDefault();
          return;
        }
        if (sessionId) {
          window.localStorage.removeItem(conversationStorageKey(sessionId));
        }
      });
    });
  }

  function bindAgentConversation() {
    const form = document.getElementById("agent-conversation-form");
    if (!form) return;
    if (form.dataset.bound === "true") return;
    form.dataset.bound = "true";

    const promptInput = document.getElementById("agent-prompt");
    const submitButton = document.getElementById("agent-submit");
    if (!promptInput || !submitButton) return;

    const sessionId = form.getAttribute("data-session-id");
    hydrateConversationFromStorage(sessionId);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const prompt = promptInput.value.trim();
      if (!prompt) return;

      const workspaceId = form.getAttribute("data-workspace-id");
      if (!workspaceId || !sessionId) return;

      appendAgentMessage("user", prompt, [], { persist: true, sessionId });
      promptInput.value = "";
      submitButton.disabled = true;
      submitButton.textContent = "Running...";

      try {
        const response = await fetch("/api/agents/prompt", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            workspace_id: workspaceId,
            session_id: sessionId,
            prompt,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.message || payload.error || "Unknown error");
        }

        appendAgentMessage("assistant", payload.response_text || "", payload.actions || [], {
          persist: true,
          sessionId,
        });
      } catch (error) {
        appendAgentMessage("assistant", `Error: ${String(error)}`, [], {
          persist: true,
          sessionId,
        });
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Send";
      }
    });
  }

  function boot() {
    bindWorkspaceSwitcher();
    bindContextFilters();
    bindContextSelection();
    bindContextPanelToggle();
    bindHtmxProgress();
    bindQuickActions();
    bindAgentSessionDeleteForms();
    bindAgentConversation();
  }

  document.addEventListener("DOMContentLoaded", boot);
  document.body.addEventListener("htmx:afterSwap", boot);
})();
