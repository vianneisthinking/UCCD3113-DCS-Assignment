import { API_BASE_URL } from "./config";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { token, ...options } = {}) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const detail = Array.isArray(data?.detail)
      ? data.detail.map((item) => item.msg).join("; ")
      : data?.detail;
    throw new ApiError(detail || `Request failed (${response.status})`, response.status);
  }
  return data;
}

export const login = (email, password) => request("/auth/login", {
  method: "POST", body: JSON.stringify({ email, password })
});

export const currentUser = (token) => request("/auth/me", { token });

export function getTickets(token, filters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.priority) params.set("priority", filters.priority);
  const suffix = params.size ? `?${params}` : "";
  return request(`/tickets${suffix}`, { token });
}

export const getStats = (token) => request("/stats", { token });
export const updateTicket = (token, id, status) => request(`/tickets/${id}`, {
  token, method: "PATCH", body: JSON.stringify({ status })
});
export const reclassifyTicket = (token, id) => request(`/tickets/${id}/reclassify`, {
  token, method: "POST"
});
