/**
 * Kanban Application Controller
 * Handles UI rendering, reactive updates, modal workflows,
 * conflict resolution dialogs, and persona switching.
 */

const App = {
  async init() {
    // Subscribe to state changes
    window.state.subscribe(() => this.render());

    // Listen for Undo/Redo state changes
    window.addEventListener("undo:change", (e) => {
      this.updateUndoRedoButtons(e.detail.canUndo, e.detail.canRedo);
    });

    // Check auth or auto-login with primary demo user
    let token = window.api.token;
    if (!token) {
      try {
        await window.api.login("sai@julley.com", "password123");
      } catch (e) {
        console.error("Auto login failed:", e);
      }
    }

    await this.loadInitialData();
    this.setupRealtimeListeners();
    this.setupUIEventListeners();
  },

  async loadInitialData() {
    try {
      const meData = await window.api.getMe();
      window.state.setCurrentUser(meData.user);
      window.state.setOrganizations(meData.organizations);

      if (window.state.currentTenant) {
        await this.loadTenantBoards(window.state.currentTenant.id);
      }
    } catch (err) {
      console.error("Error loading user state:", err);
      window.state.showToast("Failed to load initial workspace data", "error");
    }
  },

  async loadTenantBoards(tenantId) {
    try {
      const boards = await window.api.getBoards(tenantId);
      window.state.setBoards(boards);

      if (boards.length > 0) {
        await this.selectBoard(boards[0].id);
      } else {
        window.state.setBoardDetail(null);
      }
    } catch (err) {
      console.error("Error loading boards:", err);
    }
  },

  async selectBoard(boardId) {
    try {
      const boardDetail = await window.api.getBoardDetail(window.state.currentTenant.id, boardId);
      window.state.setBoardDetail(boardDetail);

      // Connect WebSocket to this scoped tenant and board channel
      window.realtime.connect(window.state.currentTenant.id, boardId);
    } catch (err) {
      console.error("Error fetching board detail:", err);
      window.state.showToast("Failed to load board details", "error");
    }
  },

  async switchPersona(email) {
    try {
      window.realtime.disconnect();
      await window.api.login(email, "password123");
      await this.loadInitialData();
      window.state.showToast(`Switched persona to ${window.state.currentUser.name}`, "success");
    } catch (err) {
      console.error("Failed to switch persona:", err);
      window.state.showToast("Failed to switch persona", "error");
    }
  },

  setupRealtimeListeners() {
    window.realtime.on("status:change", (status) => {
      this.updateConnectionStatus(status);
    });

    window.realtime.on("network:recovered", () => {
      window.state.showToast("Connection restored. Synchronizing board...", "info");
      if (window.state.currentBoard && window.state.currentTenant) {
        this.selectBoard(window.state.currentBoard.id);
      }
    });

    // Scoped Real-Time Collaboration Events
    window.realtime.on("TASK_CREATED", (payload, user) => {
      window.state.handleTaskCreated(payload);
      if (user && user.id !== window.state.currentUser.id) {
        window.state.showToast(`${user.name} created task: "${payload.title}"`, "info");
      }
    });

    window.realtime.on("TASK_UPDATED", (payload, user) => {
      window.state.handleTaskUpdated(payload);
      if (user && user.id !== window.state.currentUser.id) {
        window.state.showToast(`${user.name} updated task: "${payload.title}"`, "info");
      }
    });

    window.realtime.on("TASK_MOVED", (payload, user) => {
      window.state.handleTaskMoved(payload);
      if (user && user.id !== window.state.currentUser.id) {
        window.state.showToast(`${user.name} moved a task`, "info");
      }
    });

    window.realtime.on("TASK_DELETED", (payload, user) => {
      window.state.handleTaskDeleted(payload);
      if (user && user.id !== window.state.currentUser.id) {
        window.state.showToast(`${user.name} deleted a task`, "warning");
      }
    });

    window.realtime.on("COLUMN_CREATED", (payload) => {
      window.state.handleColumnCreated(payload);
    });

    window.realtime.on("COLUMN_UPDATED", (payload) => {
      window.state.handleColumnUpdated(payload);
    });

    window.realtime.on("COLUMN_MOVED", (payload) => {
      window.state.handleColumnMoved(payload);
    });

    window.realtime.on("COLUMN_DELETED", (payload) => {
      window.state.handleColumnDeleted(payload);
    });

    // Presence & Live Cursor Tracking
    window.realtime.on("PRESENCE_SYNC", (payload) => {
      window.state.setPresence(payload.presence);
    });

    window.realtime.on("USER_JOINED", (payload) => {
      window.state.setPresence(payload.presence);
    });

    window.realtime.on("USER_LEFT", (payload) => {
      window.state.setPresence(payload.presence);
      window.state.removeTaskFocus(payload.user_id);
    });

    window.realtime.on("USER_FOCUS_TASK", (payload) => {
      window.state.setTaskFocus(payload.user_id, payload.user_name, payload.task_id);
    });

    window.realtime.on("USER_BLUR_TASK", (payload) => {
      window.state.removeTaskFocus(payload.user_id);
    });
  },

  setupUIEventListeners() {
    // Search & Filters
    document.getElementById("search-input")?.addEventListener("input", (e) => {
      window.state.filterSearch = e.target.value.toLowerCase();
      this.renderBoard();
    });

    document.getElementById("priority-filter")?.addEventListener("change", (e) => {
      window.state.filterPriority = e.target.value;
      this.renderBoard();
    });

    // Undo / Redo buttons
    document.getElementById("btn-undo")?.addEventListener("click", () => {
      window.undoManager.undo();
    });
    document.getElementById("btn-redo")?.addEventListener("click", () => {
      window.undoManager.redo();
    });

    // New Board Modal
    document.getElementById("btn-new-board")?.addEventListener("click", () => {
      this.openNewBoardModal();
    });

    // New Column Modal
    document.getElementById("btn-new-column")?.addEventListener("click", () => {
      this.openNewColumnModal();
    });

    // Activity Log Drawer
    document.getElementById("btn-activity-log")?.addEventListener("click", () => {
      this.openActivityDrawer();
    });

    // ER Diagram Modal
    document.getElementById("btn-view-er")?.addEventListener("click", () => {
      this.openERDiagramModal();
    });
  },

  updateConnectionStatus(status) {
    const el = document.getElementById("connection-status");
    if (!el) return;

    if (status === "connected") {
      el.innerHTML = `
        <span class="relative flex h-2.5 w-2.5">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
        </span>
        <span class="text-xs font-semibold text-emerald-400">Live Sync</span>
      `;
    } else if (status === "connecting") {
      el.innerHTML = `
        <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-400 animate-pulse"></span>
        <span class="text-xs font-semibold text-amber-400">Connecting...</span>
      `;
    } else {
      el.innerHTML = `
        <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500"></span>
        <span class="text-xs font-semibold text-rose-400">Offline (Retrying)</span>
      `;
    }
  },

  updateUndoRedoButtons(canUndo, canRedo) {
    const btnUndo = document.getElementById("btn-undo");
    const btnRedo = document.getElementById("btn-redo");
    if (btnUndo) {
      btnUndo.disabled = !canUndo;
      btnUndo.classList.toggle("opacity-40", !canUndo);
      btnUndo.classList.toggle("cursor-not-allowed", !canUndo);
    }
    if (btnRedo) {
      btnRedo.disabled = !canRedo;
      btnRedo.classList.toggle("opacity-40", !canRedo);
      btnRedo.classList.toggle("cursor-not-allowed", !canRedo);
    }
  },

  render() {
    this.renderHeader();
    this.renderBoard();
  },

  renderHeader() {
    // 1. Org selector
    const orgSelect = document.getElementById("select-org");
    if (orgSelect && window.state.organizations.length > 0) {
      orgSelect.innerHTML = window.state.organizations
        .map(
          (o) =>
            `<option value="${o.id}" ${window.state.currentOrg && window.state.currentOrg.id === o.id ? "selected" : ""}>🏢 ${o.name}</option>`
        )
        .join("");

      orgSelect.onchange = (e) => {
        const selected = window.state.organizations.find((o) => o.id === e.target.value);
        if (selected) {
          window.state.setCurrentOrg(selected);
          if (window.state.currentTenant) {
            this.loadTenantBoards(window.state.currentTenant.id);
          }
        }
      };
    }

    // 2. Tenant (Branch) switcher
    const tenantSelect = document.getElementById("select-tenant");
    if (tenantSelect && window.state.currentOrg) {
      tenantSelect.innerHTML = (window.state.currentOrg.tenants || [])
        .map(
          (t) =>
            `<option value="${t.id}" ${window.state.currentTenant && window.state.currentTenant.id === t.id ? "selected" : ""}>🌿 ${t.name} (${t.location || "Branch"})</option>`
        )
        .join("");

      tenantSelect.onchange = async (e) => {
        const selected = (window.state.currentOrg.tenants || []).find((t) => t.id === e.target.value);
        if (selected) {
          window.realtime.disconnect();
          window.state.setCurrentTenant(selected);
          await this.loadTenantBoards(selected.id);
          window.state.showToast(`Switched branch to ${selected.name}`, "info");
        }
      };
    }

    // 3. Board selector
    const boardSelect = document.getElementById("select-board");
    if (boardSelect) {
      boardSelect.innerHTML = (window.state.boards || [])
        .map(
          (b) =>
            `<option value="${b.id}" ${window.state.currentBoard && window.state.currentBoard.id === b.id ? "selected" : ""}>📋 ${b.name}</option>`
        )
        .join("");

      boardSelect.onchange = (e) => {
        this.selectBoard(e.target.value);
      };
    }

    // 4. Presence Avatars Stack
    const presenceContainer = document.getElementById("presence-avatars");
    if (presenceContainer) {
      const presenceList = window.state.presence;
      if (presenceList.length === 0) {
        presenceContainer.innerHTML = `<span class="text-xs text-slate-400">Solo session</span>`;
      } else {
        presenceContainer.innerHTML = `
          <div class="flex items-center -space-x-2">
            ${presenceList
              .map(
                (p) => `
                <div class="relative group" title="${p.name} (${p.email}) - Viewing Board">
                  <div class="w-8 h-8 rounded-full border-2 border-slate-900 flex items-center justify-center text-xs font-bold text-white shadow-md transform hover:scale-110 transition-transform" style="background-color: ${p.avatar_color || "#4f46e5"}">
                    ${p.name.charAt(0).toUpperCase()}
                  </div>
                  <span class="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-400 border border-slate-900"></span>
                </div>
              `
              )
              .join("")}
          </div>
          <span class="text-xs font-medium text-slate-300 ml-2 hidden sm:inline">${presenceList.length} online</span>
        `;
      }
    }

    // 5. Active User / Role Badge
    const userBadge = document.getElementById("user-profile-badge");
    if (userBadge && window.state.currentUser) {
      userBadge.innerHTML = `
        <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 shadow-inner">
          <div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white" style="background-color: ${window.state.currentUser.avatar_color}">
            ${window.state.currentUser.name.charAt(0)}
          </div>
          <div class="flex flex-col text-left">
            <span class="text-xs font-semibold text-slate-200 leading-tight">${window.state.currentUser.name}</span>
            <span class="text-[10px] text-indigo-400 font-mono leading-tight">${window.state.currentUser.email}</span>
          </div>
        </div>
      `;
    }
  },

  renderBoard() {
    const board = window.state.currentBoard;
    const boardContainer = document.getElementById("board-columns-container");
    const boardTitleEl = document.getElementById("board-title");
    const boardDescEl = document.getElementById("board-desc");

    if (!boardContainer) return;

    if (!board) {
      boardContainer.innerHTML = `
        <div class="flex flex-col items-center justify-center w-full h-96 text-slate-400">
          <svg class="w-16 h-16 mb-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"></path>
          </svg>
          <p class="text-base font-medium">No Kanban boards found in this branch.</p>
          <button onclick="App.openNewBoardModal()" class="mt-4 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-lg transition-colors">
            + Create New Board
          </button>
        </div>
      `;
      return;
    }

    if (boardTitleEl) boardTitleEl.innerText = board.name;
    if (boardDescEl) boardDescEl.innerText = board.description || "Multi-tenant real-time collaborative workspace";

    boardContainer.innerHTML = "";

    board.columns.forEach((column) => {
      const colEl = document.createElement("div");
      colEl.className = "column-card flex-shrink-0 w-80 flex flex-col bg-slate-900/90 rounded-2xl border border-slate-800 shadow-xl overflow-hidden";
      colEl.setAttribute("data-column-id", column.id);

      // Filter tasks
      const filteredTasks = column.tasks.filter((t) => {
        const matchesSearch =
          !window.state.filterSearch ||
          t.title.toLowerCase().includes(window.state.filterSearch) ||
          (t.description && t.description.toLowerCase().includes(window.state.filterSearch)) ||
          (t.tags && t.tags.some((tag) => tag.toLowerCase().includes(window.state.filterSearch)));

        const matchesPriority =
          window.state.filterPriority === "all" || t.priority.toLowerCase() === window.state.filterPriority.toLowerCase();

        return matchesSearch && matchesPriority;
      });

      // WIP Limit Warning
      const isOverWip = column.wip_limit > 0 && column.tasks.length > column.wip_limit;
      const wipBadge = column.wip_limit > 0
        ? `<span class="px-2 py-0.5 rounded-full text-[11px] font-mono font-semibold ${isOverWip ? "bg-rose-500/20 text-rose-400 border border-rose-500/40" : "bg-slate-800 text-slate-400"}">
            ${column.tasks.length}/${column.wip_limit} WIP
           </span>`
        : `<span class="px-2 py-0.5 rounded-full text-[11px] font-mono font-medium bg-slate-800 text-slate-400">${column.tasks.length}</span>`;

      colEl.innerHTML = `
        <div class="px-4 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-850">
          <div class="flex items-center gap-2">
            <h3 class="font-semibold text-sm text-slate-200 tracking-wide">${column.title}</h3>
            ${wipBadge}
          </div>
          <div class="flex items-center gap-1">
            <button onclick="App.openNewTaskModal('${column.id}')" title="Add Task" class="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
            </button>
            <button onclick="App.deleteColumn('${column.id}')" title="Delete Column" class="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-rose-400 transition-colors">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
            </button>
          </div>
        </div>

        <div class="task-list-container flex-1 p-3 overflow-y-auto space-y-3 min-h-[350px] max-h-[calc(100vh-280px)]"></div>

        <div class="p-2 border-t border-slate-800/60 bg-slate-900/50">
          <button onclick="App.openNewTaskModal('${column.id}')" class="w-full py-2 px-3 rounded-lg border border-dashed border-slate-700/80 hover:border-indigo-500/80 hover:bg-indigo-500/5 text-xs font-medium text-slate-400 hover:text-indigo-400 flex items-center justify-center gap-1.5 transition-all">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
            Add Task
          </button>
        </div>
      `;

      const listContainer = colEl.querySelector(".task-list-container");

      // Bind Drop Zone
      window.dndManager.initColumnDropZone(listContainer, column);

      // Render Task Cards
      filteredTasks.forEach((task) => {
        const cardEl = this.createTaskCard(task);
        window.dndManager.initTaskDrag(cardEl, task);
        listContainer.appendChild(cardEl);
      });

      boardContainer.appendChild(colEl);
    });
  },

  createTaskCard(task) {
    const card = document.createElement("div");
    card.className = "task-card group relative p-3.5 rounded-xl bg-slate-800 border border-slate-700/70 hover:border-indigo-500/60 shadow-md hover:shadow-indigo-500/5 transition-all";
    card.setAttribute("data-task-id", task.id);

    // Check if peer is currently focusing this task
    const peerFocus = window.state.taskFocuses.get(task.id);
    if (peerFocus && peerFocus.userId !== window.state.currentUser?.id) {
      card.classList.add("task-focused-by-peer");
    }

    const priorityColors = {
      urgent: "bg-rose-500/15 text-rose-400 border-rose-500/30",
      high: "bg-amber-500/15 text-amber-400 border-amber-500/30",
      medium: "bg-indigo-500/15 text-indigo-400 border-indigo-500/30",
      low: "bg-slate-500/15 text-slate-400 border-slate-500/30",
    };

    const pColor = priorityColors[task.priority?.toLowerCase()] || priorityColors.medium;

    const tagsHtml = (task.tags || [])
      .map(
        (t) =>
          `<span class="px-2 py-0.5 rounded-md text-[10px] font-medium bg-slate-700/60 text-slate-300">${t}</span>`
      )
      .join("");

    const assigneeHtml = task.assignee
      ? `
        <div class="flex items-center gap-1.5" title="Assigned to ${task.assignee.name}">
          <div class="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white shadow-sm" style="background-color: ${task.assignee.avatar_color || "#3b82f6"}">
            ${task.assignee.name.charAt(0)}
          </div>
          <span class="text-[11px] text-slate-400 truncate max-w-[80px]">${task.assignee.name.split(" ")[0]}</span>
        </div>
      `
      : `<span class="text-[11px] text-slate-500 italic">Unassigned</span>`;

    const peerFocusBadge = peerFocus && peerFocus.userId !== window.state.currentUser?.id
      ? `
        <div class="flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 text-[10px] font-semibold border border-rose-500/40">
          <span class="w-1.5 h-1.5 rounded-full bg-rose-400 animate-ping"></span>
          ${peerFocus.userName} viewing
        </div>
      `
      : "";

    card.innerHTML = `
      <div class="flex items-center justify-between gap-2 mb-2">
        <span class="px-2 py-0.5 rounded-md text-[10px] font-semibold border uppercase tracking-wider ${pColor}">
          ${task.priority || "medium"}
        </span>
        <div class="flex items-center gap-1.5">
          ${peerFocusBadge}
          <span class="text-[10px] font-mono text-slate-500" title="OCC Version">v${task.version}</span>
        </div>
      </div>

      <h4 class="text-sm font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors line-clamp-2 leading-snug">
        ${task.title}
      </h4>

      ${task.description ? `<p class="mt-1 text-xs text-slate-400 line-clamp-2 leading-relaxed">${task.description}</p>` : ""}

      ${tagsHtml ? `<div class="mt-2.5 flex flex-wrap gap-1">${tagsHtml}</div>` : ""}

      <div class="mt-3 pt-2.5 border-t border-slate-700/50 flex items-center justify-between text-xs">
        ${assigneeHtml}
        <span class="text-[10px] text-slate-500 font-mono">#${task.order.toFixed(0)}</span>
      </div>
    `;

    // Click to open detail drawer
    card.addEventListener("click", (e) => {
      if (e.target.closest("button")) return;
      this.openTaskDetailDrawer(task);
    });

    return card;
  },

  // ==================== Task Detail Drawer ====================

  async openTaskDetailDrawer(task) {
    window.state.selectedTask = task;
    window.realtime.focusTask(task.id);

    const drawer = document.getElementById("task-detail-drawer");
    const backdrop = document.getElementById("drawer-backdrop");
    if (!drawer || !backdrop) return;

    drawer.classList.remove("translate-x-full");
    backdrop.classList.remove("opacity-0", "pointer-events-none");

    document.getElementById("detail-title").value = task.title;
    document.getElementById("detail-desc").value = task.description || "";
    document.getElementById("detail-priority").value = task.priority || "medium";
    document.getElementById("detail-version-badge").innerText = `v${task.version}`;
    document.getElementById("detail-tags").value = (task.tags || []).join(", ");

    // Populate assignee dropdown from tenant members
    const assigneeSelect = document.getElementById("detail-assignee");
    if (assigneeSelect) {
      try {
        const members = await window.api.getTenantMembers(window.state.currentTenant.id);
        assigneeSelect.innerHTML = `<option value="">Unassigned</option>` + members
          .map(
            (m) =>
              `<option value="${m.id}" ${task.assignee_id === m.id ? "selected" : ""}>${m.name} (${m.role})</option>`
          )
          .join("");
      } catch (err) {
        console.error(err);
      }
    }

    // Load task activity history
    this.loadTaskActivities(task.id);

    // Save button handler
    const btnSave = document.getElementById("btn-save-task");
    btnSave.onclick = async () => {
      await this.saveTaskDetails(task);
    };

    // Delete button handler
    const btnDelete = document.getElementById("btn-delete-task");
    btnDelete.onclick = async () => {
      if (confirm(`Are you sure you want to delete task "${task.title}"?`)) {
        try {
          await window.api.deleteTask(window.state.currentTenant.id, window.state.currentBoard.id, task.id);
          this.closeTaskDetailDrawer();
          window.state.showToast("Task deleted", "info");
        } catch (err) {
          window.state.showToast("Failed to delete task: " + err.message, "error");
        }
      }
    };
  },

  closeTaskDetailDrawer() {
    window.realtime.blurTask();
    window.state.selectedTask = null;

    const drawer = document.getElementById("task-detail-drawer");
    const backdrop = document.getElementById("drawer-backdrop");
    if (drawer) drawer.classList.add("translate-x-full");
    if (backdrop) backdrop.classList.add("opacity-0", "pointer-events-none");
  },

  async saveTaskDetails(task) {
    const title = document.getElementById("detail-title").value.trim();
    const description = document.getElementById("detail-desc").value.trim();
    const priority = document.getElementById("detail-priority").value;
    const assigneeId = document.getElementById("detail-assignee").value || null;
    const tagsRaw = document.getElementById("detail-tags").value;
    const tags = tagsRaw ? tagsRaw.split(",").map((s) => s.trim()).filter(Boolean) : [];

    const updatePayload = {
      title,
      description,
      priority,
      assignee_id: assigneeId,
      tags,
    };

    const previousState = {
      title: task.title,
      description: task.description,
      priority: task.priority,
      assignee_id: task.assignee_id,
      tags: task.tags,
    };

    try {
      const updated = await window.api.updateTask(
        window.state.currentTenant.id,
        window.state.currentBoard.id,
        task.id,
        updatePayload,
        task.version // OCC expected_version
      );

      // Record for undo
      window.undoManager.recordAction({
        type: "UPDATE_TASK",
        taskId: task.id,
        previousState,
        updatedState: updatePayload,
        previousVersion: task.version,
        newVersion: updated.version,
      });

      window.state.handleTaskUpdated(updated);
      this.closeTaskDetailDrawer();
      window.state.showToast("Task updated successfully", "success");
    } catch (err) {
      if (err.status === 409) {
        // Concurrency conflict detected!
        this.openConflictModal(err.conflictData, updatePayload, task);
      } else {
        window.state.showToast("Update failed: " + err.message, "error");
      }
    }
  },

  // ==================== OCC Conflict Resolution Dialog ====================

  openConflictModal(conflictData, localPayload, task) {
    const modal = document.getElementById("conflict-modal");
    if (!modal) return;

    modal.classList.remove("hidden");
    const serverTask = conflictData.server_task;

    const diffContainer = document.getElementById("conflict-diff-table");
    diffContainer.innerHTML = `
      <table class="w-full text-xs text-left">
        <thead class="bg-slate-800 text-slate-400 font-mono">
          <tr>
            <th class="p-2.5">Field</th>
            <th class="p-2.5 text-rose-400">Your Local Changes (v${conflictData.client_version})</th>
            <th class="p-2.5 text-emerald-400">Server's Latest Version (v${conflictData.server_version})</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800 text-slate-300">
          <tr>
            <td class="p-2.5 font-semibold text-slate-400">Title</td>
            <td class="p-2.5">${localPayload.title}</td>
            <td class="p-2.5 font-medium text-emerald-300">${serverTask.title}</td>
          </tr>
          <tr>
            <td class="p-2.5 font-semibold text-slate-400">Priority</td>
            <td class="p-2.5 uppercase font-mono">${localPayload.priority}</td>
            <td class="p-2.5 uppercase font-mono text-emerald-300">${serverTask.priority}</td>
          </tr>
          <tr>
            <td class="p-2.5 font-semibold text-slate-400">Description</td>
            <td class="p-2.5 max-w-xs truncate">${localPayload.description || "<empty>"}</td>
            <td class="p-2.5 max-w-xs truncate text-emerald-300">${serverTask.description || "<empty>"}</td>
          </tr>
        </tbody>
      </table>
    `;

    // Strategy 1: Keep Server Version
    document.getElementById("btn-conflict-server").onclick = () => {
      window.state.handleTaskUpdated(serverTask);
      modal.classList.add("hidden");
      this.openTaskDetailDrawer(serverTask);
      window.state.showToast("Accepted latest server version", "info");
    };

    // Strategy 2: Overwrite with My Changes
    document.getElementById("btn-conflict-overwrite").onclick = async () => {
      modal.classList.add("hidden");
      try {
        const overwritten = await window.api.updateTask(
          window.state.currentTenant.id,
          window.state.currentBoard.id,
          task.id,
          localPayload,
          serverTask.version // use latest server version to overwrite
        );
        window.state.handleTaskUpdated(overwritten);
        this.closeTaskDetailDrawer();
        window.state.showToast("Overwritten with your changes", "success");
      } catch (e) {
        window.state.showToast("Overwrite failed: " + e.message, "error");
      }
    };

    // Strategy 3: Merge
    document.getElementById("btn-conflict-merge").onclick = async () => {
      modal.classList.add("hidden");
      // Merge: take local title and description, keep server priority & assignee
      const mergedPayload = {
        title: localPayload.title,
        description: localPayload.description || serverTask.description,
        priority: serverTask.priority,
        assignee_id: serverTask.assignee_id,
        tags: Array.from(new Set([...(localPayload.tags || []), ...(serverTask.tags || [])])),
      };
      try {
        const merged = await window.api.updateTask(
          window.state.currentTenant.id,
          window.state.currentBoard.id,
          task.id,
          mergedPayload,
          serverTask.version
        );
        window.state.handleTaskUpdated(merged);
        this.closeTaskDetailDrawer();
        window.state.showToast("Merged changes applied successfully", "success");
      } catch (e) {
        window.state.showToast("Merge failed: " + e.message, "error");
      }
    };
  },

  async loadTaskActivities(taskId) {
    const listEl = document.getElementById("task-activity-list");
    if (!listEl) return;

    try {
      const logs = await window.api.request(`/tenants/${window.state.currentTenant.id}/activities?task_id=${taskId}&limit=20`);
      if (logs.length === 0) {
        listEl.innerHTML = `<p class="text-xs text-slate-500 italic">No activity recorded yet for this task.</p>`;
        return;
      }

      listEl.innerHTML = logs
        .map(
          (log) => `
          <div class="flex items-start gap-2.5 text-xs py-2 border-b border-slate-800/60 last:border-0">
            <div class="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0" style="background-color: ${log.user?.avatar_color || "#6366f1"}">
              ${log.user?.name ? log.user.name.charAt(0) : "S"}
            </div>
            <div class="flex-1">
              <p class="text-slate-300">
                <span class="font-semibold text-slate-200">${log.user?.name || "User"}</span>
                ${this.formatActionLabel(log.action, log.details)}
              </p>
              <span class="text-[10px] text-slate-500">${new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
          </div>
        `
        )
        .join("");
    } catch (e) {
      listEl.innerHTML = `<p class="text-xs text-slate-500">Failed to load history.</p>`;
    }
  },

  formatActionLabel(action, details = {}) {
    switch (action) {
      case "TASK_CREATED":
        return `created this task in <strong class="text-indigo-300">${details.column || "board"}</strong>`;
      case "TASK_MOVED":
        return `moved task to <strong class="text-indigo-300">${details.to_column_title || "new column"}</strong>`;
      case "TASK_UPDATED":
        return `updated task details (v${details.new_version || ""})`;
      case "TASK_DELETED":
        return `deleted this task`;
      default:
        return `performed action ${action}`;
    }
  },

  // ==================== Modals & Drawers ====================

  openNewTaskModal(columnId) {
    const modal = document.getElementById("new-task-modal");
    if (!modal) return;
    modal.classList.remove("hidden");
    document.getElementById("new-task-col-id").value = columnId;
    document.getElementById("new-task-title").value = "";
    document.getElementById("new-task-desc").value = "";
    document.getElementById("new-task-title").focus();

    const form = document.getElementById("new-task-form");
    form.onsubmit = async (e) => {
      e.preventDefault();
      const title = document.getElementById("new-task-title").value.trim();
      const description = document.getElementById("new-task-desc").value.trim();
      const priority = document.getElementById("new-task-priority").value;
      const targetColId = document.getElementById("new-task-col-id").value;

      try {
        await window.api.createTask(
          window.state.currentTenant.id,
          window.state.currentBoard.id,
          targetColId,
          { title, description, priority }
        );
        modal.classList.add("hidden");
        window.state.showToast("Task created successfully", "success");
      } catch (err) {
        window.state.showToast("Failed to create task: " + err.message, "error");
      }
    };
  },

  openNewColumnModal() {
    const modal = document.getElementById("new-column-modal");
    if (!modal) return;
    modal.classList.remove("hidden");
    document.getElementById("new-col-title").value = "";
    document.getElementById("new-col-wip").value = "0";

    const form = document.getElementById("new-column-form");
    form.onsubmit = async (e) => {
      e.preventDefault();
      const title = document.getElementById("new-col-title").value.trim();
      const wipLimit = parseInt(document.getElementById("new-col-wip").value) || 0;

      try {
        await window.api.createColumn(
          window.state.currentTenant.id,
          window.state.currentBoard.id,
          title,
          wipLimit
        );
        modal.classList.add("hidden");
        window.state.showToast("Column created successfully", "success");
      } catch (err) {
        window.state.showToast("Failed to create column: " + err.message, "error");
      }
    };
  },

  async deleteColumn(columnId) {
    if (confirm("Are you sure you want to delete this column and all its tasks?")) {
      try {
        await window.api.deleteColumn(window.state.currentTenant.id, window.state.currentBoard.id, columnId);
        window.state.showToast("Column deleted", "info");
      } catch (err) {
        window.state.showToast("Failed to delete column: " + err.message, "error");
      }
    }
  },

  openNewBoardModal() {
    const modal = document.getElementById("new-board-modal");
    if (!modal) return;
    modal.classList.remove("hidden");
    document.getElementById("new-board-name").value = "";
    document.getElementById("new-board-desc").value = "";

    const form = document.getElementById("new-board-form");
    form.onsubmit = async (e) => {
      e.preventDefault();
      const name = document.getElementById("new-board-name").value.trim();
      const description = document.getElementById("new-board-desc").value.trim();
      const color = document.getElementById("new-board-color").value || "#4f46e5";

      try {
        const newBoard = await window.api.createBoard(
          window.state.currentTenant.id,
          name,
          description,
          color
        );
        modal.classList.add("hidden");
        await this.loadTenantBoards(window.state.currentTenant.id);
        await this.selectBoard(newBoard.id);
        window.state.showToast("Board created successfully", "success");
      } catch (err) {
        window.state.showToast("Failed to create board: " + err.message, "error");
      }
    };
  },

  async openActivityDrawer() {
    const drawer = document.getElementById("activity-log-drawer");
    const backdrop = document.getElementById("activity-backdrop");
    if (!drawer || !backdrop) return;

    drawer.classList.remove("translate-x-full");
    backdrop.classList.remove("opacity-0", "pointer-events-none");

    const listEl = document.getElementById("tenant-activity-stream");
    listEl.innerHTML = `<div class="p-4 text-xs text-slate-400">Loading tenant activities...</div>`;

    try {
      const activities = await window.api.getActivities(window.state.currentTenant.id);
      if (activities.length === 0) {
        listEl.innerHTML = `<div class="p-4 text-xs text-slate-400 italic">No activity recorded for this branch yet.</div>`;
        return;
      }

      listEl.innerHTML = activities
        .map(
          (act) => `
          <div class="p-3.5 border-b border-slate-800/80 hover:bg-slate-800/40 transition-colors">
            <div class="flex items-center justify-between mb-1">
              <span class="text-[10px] font-mono font-semibold uppercase px-2 py-0.5 rounded bg-slate-800 text-indigo-400 border border-slate-700/60">
                ${act.action}
              </span>
              <span class="text-[10px] text-slate-500">${new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
            </div>
            <div class="flex items-center gap-2 mt-2">
              <div class="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0" style="background-color: ${act.user?.avatar_color || "#6366f1"}">
                ${act.user?.name ? act.user.name.charAt(0) : "U"}
              </div>
              <p class="text-xs text-slate-300">
                <span class="font-semibold text-slate-200">${act.user?.name || "System"}</span>:
                ${this.formatActionLabel(act.action, act.details)}
              </p>
            </div>
          </div>
        `
        )
        .join("");
    } catch (err) {
      listEl.innerHTML = `<div class="p-4 text-xs text-rose-400">Failed to load activity logs.</div>`;
    }
  },

  closeActivityDrawer() {
    const drawer = document.getElementById("activity-log-drawer");
    const backdrop = document.getElementById("activity-backdrop");
    if (drawer) drawer.classList.add("translate-x-full");
    if (backdrop) backdrop.classList.add("opacity-0", "pointer-events-none");
  },

  openERDiagramModal() {
    const modal = document.getElementById("er-diagram-modal");
    if (modal) modal.classList.remove("hidden");
  },

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add("hidden");
  },
};

window.App = App;
document.addEventListener("DOMContentLoaded", () => App.init());
