/**
 * REST API client with automatic token injection, error handling,
 * and 409 Conflict extraction for Optimistic Concurrency Control.
 */
class ApiClient {
  constructor() {
    this.token = localStorage.getItem("kanban_token") || null;
    this.user = JSON.parse(localStorage.getItem("kanban_user") || "null");
  }

  setAuth(token, user) {
    this.token = token;
    this.user = user;
    localStorage.setItem("kanban_token", token);
    localStorage.setItem("kanban_user", JSON.stringify(user));
  }

  clearAuth() {
    this.token = null;
    this.user = null;
    localStorage.removeItem("kanban_token");
    localStorage.removeItem("kanban_user");
  }

  async request(endpoint, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(`/api${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 409) {
      const errData = await response.json();
      const conflictError = new Error("Conflict detected");
      conflictError.status = 409;
      conflictError.conflictData = errData.detail;
      throw conflictError;
    }

    if (response.status === 401) {
      this.clearAuth();
      window.dispatchEvent(new CustomEvent("auth:required"));
      throw new Error("Authentication session expired");
    }

    if (!response.ok) {
      let errMsg = `Request failed with status ${response.status}`;
      try {
        const errJson = await response.json();
        errMsg = errJson.detail || errMsg;
      } catch (e) {}
      const error = new Error(errMsg);
      error.status = response.status;
      throw error;
    }

    if (response.status === 204) return null;
    return await response.json();
  }

  // Auth & Personas
  async login(email, password) {
    const data = await this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    this.setAuth(data.access_token, data.user);
    return data;
  }

  async getMe() {
    return await this.request("/auth/me");
  }

  async getDemoUsers() {
    return await this.request("/auth/demo-users");
  }

  // Organizations & Tenants
  async getOrganizations() {
    return await this.request("/organizations");
  }

  async createTenant(orgId, name, slug, location) {
    return await this.request(`/organizations/${orgId}/tenants`, {
      method: "POST",
      body: JSON.stringify({ name, slug, location }),
    });
  }

  async getTenantMembers(tenantId) {
    return await this.request(`/tenants/${tenantId}/members`);
  }

  async addTenantMember(tenantId, email, role) {
    return await this.request(`/tenants/${tenantId}/members`, {
      method: "POST",
      body: JSON.stringify({ email, role }),
    });
  }

  // Boards
  async getBoards(tenantId) {
    return await this.request(`/tenants/${tenantId}/boards`);
  }

  async createBoard(tenantId, name, description, color) {
    return await this.request(`/tenants/${tenantId}/boards`, {
      method: "POST",
      body: JSON.stringify({ name, description, color }),
    });
  }

  async getBoardDetail(tenantId, boardId) {
    return await this.request(`/tenants/${tenantId}/boards/${boardId}`);
  }

  // Columns
  async createColumn(tenantId, boardId, title, wipLimit = 0) {
    return await this.request(`/tenants/${tenantId}/boards/${boardId}/columns`, {
      method: "POST",
      body: JSON.stringify({ title, wip_limit: wipLimit }),
    });
  }

  async moveColumn(tenantId, boardId, columnId, prevOrder, nextOrder) {
    return await this.request(`/tenants/${tenantId}/boards/${boardId}/columns/${columnId}/move`, {
      method: "POST",
      body: JSON.stringify({ prev_order: prevOrder, next_order: nextOrder }),
    });
  }

  async deleteColumn(tenantId, boardId, columnId) {
    return await this.request(`/tenants/${tenantId}/boards/${boardId}/columns/${columnId}`, {
      method: "DELETE",
    });
  }

  // Tasks
  async createTask(tenantId, boardId, columnId, taskData) {
    return await this.request(`/tenants/${tenantId}/boards/${boardId}/tasks`, {
      method: "POST",
      body: JSON.stringify({ ...taskData, column_id: columnId }),
    });
  }

  async updateTask(tenantId, boardId, taskId, updateData, expectedVersion) {
    return await this.request(`/tenants/${tenantId}/boards/${boardId}/tasks/${taskId}`, {
      method: "PUT",
      body: JSON.stringify({ ...updateData, expected_version: expectedVersion }),
    });
  }

  async moveTask(tenantId, boardId, taskId, targetColumnId, prevOrder, nextOrder, expectedVersion = null) {
    return await this.request(`/tenants/${tenantId}/boards/${boardId}/tasks/${taskId}/move`, {
      method: "POST",
      body: JSON.stringify({
        target_column_id: targetColumnId,
        prev_order: prevOrder,
        next_order: nextOrder,
        expected_version: expectedVersion,
      }),
    });
  }

  async deleteTask(tenantId, boardId, taskId) {
    return await this.request(`/tenants/${tenantId}/boards/${boardId}/tasks/${taskId}`, {
      method: "DELETE",
    });
  }

  // Activity Logs
  async getActivities(tenantId, boardId = null, limit = 50) {
    let url = `/tenants/${tenantId}/activities?limit=${limit}`;
    if (boardId) url += `&board_id=${boardId}`;
    return await this.request(url);
  }
}

window.api = new ApiClient();
