/**
 * Undo / Redo Manager for Collaborative Kanban Actions.
 * Supports task moves, updates, and state rollbacks with keyboard shortcuts.
 */
class UndoManager {
  constructor() {
    this.undoStack = [];
    this.redoStack = [];
    this.maxHistory = 50;
    this.isApplying = false;

    // Attach global keyboard shortcuts
    window.addEventListener("keydown", (e) => {
      // Ignore if focus is in an input or textarea
      if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
        return;
      }

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        if (e.shiftKey) {
          e.preventDefault();
          this.redo();
        } else {
          e.preventDefault();
          this.undo();
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
        e.preventDefault();
        this.redo();
      }
    });
  }

  recordAction(action) {
    if (this.isApplying) return;
    this.undoStack.push(action);
    if (this.undoStack.length > this.maxHistory) {
      this.undoStack.shift();
    }
    this.redoStack = []; // Clear redo on new action
    this.notifyChange();
  }

  canUndo() {
    return this.undoStack.length > 0;
  }

  canRedo() {
    return this.redoStack.length > 0;
  }

  async undo() {
    if (!this.canUndo() || this.isApplying) return;
    const action = this.undoStack.pop();
    this.redoStack.push(action);
    this.isApplying = true;

    try {
      if (action.type === "MOVE_TASK") {
        const { taskId, sourceColId, originalOrder, originalVersion } = action;
        await window.api.moveTask(
          window.state.currentTenant.id,
          window.state.currentBoard.id,
          taskId,
          sourceColId,
          originalOrder - 1.0,
          originalOrder + 1.0,
          originalVersion
        );
        window.state.showToast("Undid task move", "info");
      } else if (action.type === "UPDATE_TASK") {
        const { taskId, previousState, newVersion } = action;
        await window.api.updateTask(
          window.state.currentTenant.id,
          window.state.currentBoard.id,
          taskId,
          previousState,
          newVersion
        );
        window.state.showToast("Undid task edit", "info");
      }
    } catch (err) {
      console.error("Failed to apply undo:", err);
      window.state.showToast("Failed to undo action (state may have changed)", "error");
    } finally {
      this.isApplying = false;
      this.notifyChange();
    }
  }

  async redo() {
    if (!this.canRedo() || this.isApplying) return;
    const action = this.redoStack.pop();
    this.undoStack.push(action);
    this.isApplying = true;

    try {
      if (action.type === "MOVE_TASK") {
        const { taskId, targetColId, newOrder, newVersion } = action;
        await window.api.moveTask(
          window.state.currentTenant.id,
          window.state.currentBoard.id,
          taskId,
          targetColId,
          newOrder - 1.0,
          newOrder + 1.0,
          newVersion
        );
        window.state.showToast("Redid task move", "info");
      } else if (action.type === "UPDATE_TASK") {
        const { taskId, updatedState, previousVersion } = action;
        await window.api.updateTask(
          window.state.currentTenant.id,
          window.state.currentBoard.id,
          taskId,
          updatedState,
          previousVersion
        );
        window.state.showToast("Redid task edit", "info");
      }
    } catch (err) {
      console.error("Failed to apply redo:", err);
      window.state.showToast("Failed to redo action", "error");
    } finally {
      this.isApplying = false;
      this.notifyChange();
    }
  }

  notifyChange() {
    window.dispatchEvent(new CustomEvent("undo:change", {
      detail: { canUndo: this.canUndo(), canRedo: this.canRedo() }
    }));
  }
}

window.undoManager = new UndoManager();
