/**
 * Central state store with reactive subscriptions and optimistic mutations.
 */
class StateStore {
  constructor() {
    this.currentUser = null;
    this.organizations = [];
    this.currentOrg = null;
    this.currentTenant = null;
    this.boards = [];
    this.currentBoard = null; // Board with columns & tasks
    this.presence = []; // Active users viewing board
    this.taskFocuses = new Map(); // taskId -> { userId, userName }
    this.activities = [];
    this.selectedTask = null; // For detail drawer
    this.conflictData = null; // For conflict modal

    // Filters
    this.filterSearch = "";
    this.filterPriority = "all";
    this.filterAssignee = "all";

    this.subscribers = new Set();
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  notify() {
    this.subscribers.forEach((cb) => cb(this));
  }

  setCurrentUser(user) {
    this.currentUser = user;
    this.notify();
  }

  setOrganizations(orgs) {
    this.organizations = orgs;
    if (orgs.length > 0 && !this.currentOrg) {
      this.currentOrg = orgs[0];
      if (this.currentOrg.tenants && this.currentOrg.tenants.length > 0) {
        this.currentTenant = this.currentOrg.tenants[0];
      }
    }
    this.notify();
  }

  setCurrentOrg(org) {
    this.currentOrg = org;
    if (org.tenants && org.tenants.length > 0) {
      this.setCurrentTenant(org.tenants[0]);
    } else {
      this.currentTenant = null;
      this.currentBoard = null;
    }
    this.notify();
  }

  setCurrentTenant(tenant) {
    this.currentTenant = tenant;
    this.currentBoard = null;
    this.notify();
  }

  setBoards(boards) {
    this.boards = boards;
    if (boards.length > 0 && !this.currentBoard) {
      this.currentBoard = boards[0];
    }
    this.notify();
  }

  setBoardDetail(boardDetail) {
    this.currentBoard = boardDetail;
    this.notify();
  }

  // Real-time & Optimistic mutations
  handleTaskCreated(task) {
    if (!this.currentBoard) return;
    const col = this.currentBoard.columns.find((c) => c.id === task.column_id);
    if (col) {
      if (!col.tasks.some((t) => t.id === task.id)) {
        col.tasks.push(task);
        col.tasks.sort((a, b) => a.order - b.order);
      }
    }
    this.notify();
  }

  handleTaskUpdated(updatedTask) {
    if (!this.currentBoard) return;
    for (const col of this.currentBoard.columns) {
      const idx = col.tasks.findIndex((t) => t.id === updatedTask.id);
      if (idx !== -1) {
        col.tasks[idx] = { ...col.tasks[idx], ...updatedTask };
        if (this.selectedTask && this.selectedTask.id === updatedTask.id) {
          this.selectedTask = col.tasks[idx];
        }
        break;
      }
    }
    this.notify();
  }

  handleTaskMoved({ task_id, source_column_id, target_column_id, order, version, task }) {
    if (!this.currentBoard) return;

    // Find and remove task from whatever column currently holds it
    let foundTask = null;
    for (const col of this.currentBoard.columns) {
      const idx = col.tasks.findIndex((t) => t.id === task_id);
      if (idx !== -1) {
        foundTask = col.tasks.splice(idx, 1)[0];
        break;
      }
    }

    if (!foundTask && task) {
      foundTask = task;
    }

    if (foundTask) {
      foundTask.column_id = target_column_id;
      foundTask.order = order;
      foundTask.version = version;

      const targetCol = this.currentBoard.columns.find((c) => c.id === target_column_id);
      if (targetCol) {
        targetCol.tasks.push(foundTask);
        targetCol.tasks.sort((a, b) => a.order - b.order);
      }

      if (this.selectedTask && this.selectedTask.id === task_id) {
        this.selectedTask = foundTask;
      }
    }

    this.notify();
  }

  handleTaskDeleted({ task_id }) {
    if (!this.currentBoard) return;
    for (const col of this.currentBoard.columns) {
      col.tasks = col.tasks.filter((t) => t.id !== task_id);
    }
    if (this.selectedTask && this.selectedTask.id === task_id) {
      this.selectedTask = null;
    }
    this.notify();
  }

  handleColumnCreated(column) {
    if (!this.currentBoard) return;
    if (!this.currentBoard.columns.some((c) => c.id === column.id)) {
      this.currentBoard.columns.push({ ...column, tasks: [] });
      this.currentBoard.columns.sort((a, b) => a.order - b.order);
    }
    this.notify();
  }

  handleColumnUpdated(updatedCol) {
    if (!this.currentBoard) return;
    const col = this.currentBoard.columns.find((c) => c.id === updatedCol.id);
    if (col) {
      Object.assign(col, updatedCol);
    }
    this.notify();
  }

  handleColumnMoved(movedCol) {
    if (!this.currentBoard) return;
    const col = this.currentBoard.columns.find((c) => c.id === movedCol.id);
    if (col) {
      col.order = movedCol.order;
      this.currentBoard.columns.sort((a, b) => a.order - b.order);
    }
    this.notify();
  }

  handleColumnDeleted({ id }) {
    if (!this.currentBoard) return;
    this.currentBoard.columns = this.currentBoard.columns.filter((c) => c.id !== id);
    this.notify();
  }

  setPresence(list) {
    this.presence = list || [];
    this.notify();
  }

  setTaskFocus(userId, userName, taskId) {
    if (taskId) {
      this.taskFocuses.set(taskId, { userId, userName });
    } else {
      for (const [tId, val] of this.taskFocuses.entries()) {
        if (val.userId === userId) {
          this.taskFocuses.delete(tId);
        }
      }
    }
    this.notify();
  }

  removeTaskFocus(userId) {
    for (const [tId, val] of this.taskFocuses.entries()) {
      if (val.userId === userId) {
        this.taskFocuses.delete(tId);
      }
    }
    this.notify();
  }

  showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    const bgColors = {
      info: "bg-indigo-600 border-indigo-400 text-white",
      success: "bg-emerald-600 border-emerald-400 text-white",
      error: "bg-rose-600 border-rose-400 text-white",
      warning: "bg-amber-600 border-amber-400 text-white",
    };

    toast.className = `flex items-center gap-2 px-4 py-3 rounded-lg shadow-xl border text-sm font-medium transition-all duration-300 transform translate-y-2 opacity-0 ${bgColors[type] || bgColors.info}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.remove("translate-y-2", "opacity-0");
    }, 10);

    setTimeout(() => {
      toast.classList.add("opacity-0", "translate-y-2");
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }
}

window.state = new StateStore();
