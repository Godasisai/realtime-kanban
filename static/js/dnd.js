/**
 * Drag and Drop Manager using Native HTML5 Drag and Drop API.
 * Computes Fractional Indexing midpoint positions (O(1) updates)
 * and applies optimistic updates with automatic rollback on error.
 */
class DragDropManager {
  constructor() {
    this.draggedTaskId = null;
    this.draggedColId = null;
    this.sourceColId = null;
    this.draggedTaskElement = null;
    this.dropPlaceholder = null;
  }

  initTaskDrag(taskElement, task) {
    taskElement.setAttribute("draggable", "true");

    taskElement.addEventListener("dragstart", (e) => {
      this.draggedTaskId = task.id;
      this.sourceColId = task.column_id;
      this.draggedTaskElement = taskElement;
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", task.id);
      setTimeout(() => taskElement.classList.add("dragging"), 0);
    });

    taskElement.addEventListener("dragend", () => {
      taskElement.classList.remove("dragging");
      this.removeDropPlaceholder();
      this.draggedTaskId = null;
      this.draggedTaskElement = null;
      this.sourceColId = null;
    });
  }

  initColumnDropZone(columnBodyElement, column) {
    columnBodyElement.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      columnBodyElement.classList.add("drop-target-active");

      // Calculate where to place placeholder among children
      const afterElement = this.getDragAfterElement(columnBodyElement, e.clientY);
      if (!this.dropPlaceholder) {
        this.dropPlaceholder = document.createElement("div");
        this.dropPlaceholder.className = "h-16 rounded-xl border-2 border-dashed border-indigo-400 bg-indigo-500/10 mb-3 transition-all";
      }

      if (afterElement == null) {
        columnBodyElement.appendChild(this.dropPlaceholder);
      } else {
        columnBodyElement.insertBefore(this.dropPlaceholder, afterElement);
      }
    });

    columnBodyElement.addEventListener("dragleave", (e) => {
      if (!columnBodyElement.contains(e.relatedTarget)) {
        columnBodyElement.classList.remove("drop-target-active");
        this.removeDropPlaceholder();
      }
    });

    columnBodyElement.addEventListener("drop", async (e) => {
      e.preventDefault();
      columnBodyElement.classList.remove("drop-target-active");

      const taskId = e.dataTransfer.getData("text/plain") || this.draggedTaskId;
      if (!taskId) return;

      const targetColId = column.id;
      const targetCol = window.state.currentBoard.columns.find((c) => c.id === targetColId);
      if (!targetCol) return;

      // Find the task in state
      let currentTask = null;
      let originalColId = null;
      for (const col of window.state.currentBoard.columns) {
        const t = col.tasks.find((item) => item.id === taskId);
        if (t) {
          currentTask = { ...t };
          originalColId = col.id;
          break;
        }
      }
      if (!currentTask) return;

      // Calculate prev_order and next_order based on placeholder position
      const afterElement = this.getDragAfterElement(columnBodyElement, e.clientY);
      this.removeDropPlaceholder();

      // Collect sibling tasks in target column excluding the dragged task
      const remainingTasks = targetCol.tasks.filter((t) => t.id !== taskId);

      let prevOrder = null;
      let nextOrder = null;

      if (!afterElement) {
        // Dropped at bottom
        if (remainingTasks.length > 0) {
          prevOrder = remainingTasks[remainingTasks.length - 1].order;
          nextOrder = null;
        } else {
          prevOrder = null;
          nextOrder = null;
        }
      } else {
        const afterTaskId = afterElement.getAttribute("data-task-id");
        const afterIndex = remainingTasks.findIndex((t) => t.id === afterTaskId);

        if (afterIndex === 0) {
          // Dropped at top
          prevOrder = null;
          nextOrder = remainingTasks[0].order;
        } else if (afterIndex > 0) {
          // Dropped between
          prevOrder = remainingTasks[afterIndex - 1].order;
          nextOrder = remainingTasks[afterIndex].order;
        }
      }

      // Calculate optimistic order
      let optimisticOrder = 1000.0;
      if (prevOrder !== null && nextOrder !== null) {
        optimisticOrder = (prevOrder + nextOrder) / 2.0;
      } else if (prevOrder !== null) {
        optimisticOrder = prevOrder + 1000.0;
      } else if (nextOrder !== null) {
        optimisticOrder = nextOrder / 2.0;
      }

      // Record for Undo
      window.undoManager.recordAction({
        type: "MOVE_TASK",
        taskId: taskId,
        sourceColId: originalColId,
        targetColId: targetColId,
        originalOrder: currentTask.order,
        originalVersion: currentTask.version,
        newOrder: optimisticOrder,
        newVersion: currentTask.version + 1,
      });

      // Optimistic update
      window.state.handleTaskMoved({
        task_id: taskId,
        source_column_id: originalColId,
        target_column_id: targetColId,
        order: optimisticOrder,
        version: currentTask.version + 1,
        task: { ...currentTask, column_id: targetColId, order: optimisticOrder },
      });

      // Send to server
      try {
        await window.api.moveTask(
          window.state.currentTenant.id,
          window.state.currentBoard.id,
          taskId,
          targetColId,
          prevOrder,
          nextOrder,
          currentTask.version
        );
      } catch (err) {
        console.error("Failed to move task on server:", err);
        // Rollback optimistic update
        window.state.handleTaskMoved({
          task_id: taskId,
          source_column_id: targetColId,
          target_column_id: originalColId,
          order: currentTask.order,
          version: currentTask.version,
          task: currentTask,
        });
        window.state.showToast("Failed to move task: " + err.message, "error");
      }
    });
  }

  getDragAfterElement(container, y) {
    const draggableElements = [
      ...container.querySelectorAll(".task-card:not(.dragging)"),
    ];

    return draggableElements.reduce(
      (closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
          return { offset: offset, element: child };
        } else {
          return closest;
        }
      },
      { offset: Number.NEGATIVE_INFINITY }
    ).element;
  }

  removeDropPlaceholder() {
    if (this.dropPlaceholder && this.dropPlaceholder.parentNode) {
      this.dropPlaceholder.parentNode.removeChild(this.dropPlaceholder);
    }
  }
}

window.dndManager = new DragDropManager();
