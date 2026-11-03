/**
 * Scoped WebSocket Client for real-time collaboration,
 * presence tracking, task focus notifications, and auto-reconnection.
 */
class RealtimeClient {
  constructor() {
    this.ws = null;
    this.tenantId = null;
    this.boardId = null;
    this.status = "disconnected"; // connected, connecting, disconnected
    this.listeners = new Map();
    this.reconnectTimer = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.pingTimer = null;
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    if (!this.listeners.has(event)) return;
    this.listeners.set(
      event,
      this.listeners.get(event).filter((cb) => cb !== callback)
    );
  }

  emit(event, data) {
    const handlers = this.listeners.get(event) || [];
    handlers.forEach((cb) => {
      try {
        cb(data);
      } catch (e) {
        console.error("Error in WS event handler:", e);
      }
    });
  }

  connect(tenantId, boardId) {
    if (this.ws) {
      this.disconnect();
    }

    this.tenantId = tenantId;
    this.boardId = boardId;
    this.status = "connecting";
    this.emit("status:change", this.status);

    const token = window.api.token;
    if (!token || !tenantId || !boardId) {
      this.status = "disconnected";
      this.emit("status:change", this.status);
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws?token=${encodeURIComponent(token)}&tenant_id=${encodeURIComponent(tenantId)}&board_id=${encodeURIComponent(boardId)}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.status = "connected";
        this.reconnectAttempts = 0;
        this.emit("status:change", this.status);
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "PONG") return;
          this.emit(message.type, message.payload, message.user);
          this.emit("*", message);
        } catch (err) {
          console.error("Error parsing WS frame:", err);
        }
      };

      this.ws.onclose = (event) => {
        this.cleanup();
        this.status = "disconnected";
        this.emit("status:change", this.status);

        // Auto reconnect unless intentionally closed
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 10000);
          this.reconnectAttempts++;
          this.reconnectTimer = setTimeout(() => {
            if (this.tenantId && this.boardId) {
              this.connect(this.tenantId, this.boardId);
              // Trigger state refresh on network recovery
              this.emit("network:recovered");
            }
          }, delay);
        }
      };

      this.ws.onerror = (err) => {
        console.warn("WebSocket error:", err);
      };
    } catch (e) {
      this.status = "disconnected";
      this.emit("status:change", this.status);
    }
  }

  disconnect() {
    this.cleanup();
    if (this.ws) {
      try {
        this.ws.close(1000, "Normal closure");
      } catch (e) {}
      this.ws = null;
    }
    this.tenantId = null;
    this.boardId = null;
    this.status = "disconnected";
    this.emit("status:change", this.status);
  }

  cleanup() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  startHeartbeat() {
    this.pingTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "PING" }));
      }
    }, 25000);
  }

  send(type, payload = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...payload }));
    }
  }

  focusTask(taskId) {
    this.send("FOCUS_TASK", { task_id: taskId });
  }

  blurTask() {
    this.send("BLUR_TASK");
  }
}

window.realtime = new RealtimeClient();
