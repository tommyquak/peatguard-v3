"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "./authStore";
import type {
  Aoi,
  Message,
  Payment,
  Task,
  TaskStatus,
  User,
  Village,
  Worker,
} from "./types";

// All requests go to relative /api/v1 -- next.config rewrites proxy to the
// FastAPI backend (configurable via NEXT_PUBLIC_API_BASE).

async function request<T>(
  path: string,
  init: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const body = await res.json();
      detail = body?.detail;
    } catch {}
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ---- Auth ----
export function useLogin() {
  const setSession = useAuth((s) => s.setSession);
  return useMutation({
    mutationFn: async (vars: { email: string; password: string }) => {
      const data = await request<{ token: string; user: User }>("/auth/login", {
        method: "POST",
        body: JSON.stringify(vars),
      });
      setSession(data.token, data.user);
      return data;
    },
  });
}

// ---- AOIs ----
export function useAois() {
  return useQuery({
    queryKey: ["aois"],
    queryFn: () => request<Aoi[]>("/aois"),
  });
}
export function useAoi(code: string | null) {
  return useQuery({
    queryKey: ["aoi", code],
    queryFn: () => request<Aoi>(`/aois/${code}`),
    enabled: !!code,
  });
}

// ---- Villages ----
export function useVillages() {
  return useQuery({
    queryKey: ["villages"],
    queryFn: () => request<Village[]>("/villages"),
  });
}

// ---- Workers ----
export function useWorkers() {
  return useQuery({
    queryKey: ["workers"],
    queryFn: () => request<Worker[]>("/workers"),
  });
}

// ---- Products (raster catalog) ----
export interface ProductMeta {
  id: string;
  filename: string;
  label: string;
  description: string;
  tile_url: string;
  cog_url: string;
  colormap: string;
  rescale: string;
  legend_type: string;
  legend_labels: string[];
  legend_colors: string[];
  default_on: boolean;
}
export function useProducts() {
  return useQuery({
    queryKey: ["products"],
    queryFn: async () => (await request<{ products: ProductMeta[] }>("/products")).products,
  });
}

// ---- Tasks ----
export function useTasks(filter?: {
  status?: TaskStatus;
  worker_id?: string;
  village_id?: string;
  aoi_code?: string;
}) {
  const params = new URLSearchParams();
  if (filter?.status) params.set("status", filter.status);
  if (filter?.worker_id) params.set("worker_id", filter.worker_id);
  if (filter?.village_id) params.set("village_id", filter.village_id);
  if (filter?.aoi_code) params.set("aoi_code", filter.aoi_code);
  const qs = params.toString() ? `?${params}` : "";
  return useQuery({
    queryKey: ["tasks", filter || {}],
    queryFn: () => request<Task[]>(`/tasks${qs}`),
  });
}

export function useTask(id: string | null) {
  return useQuery({
    queryKey: ["task", id],
    queryFn: () => request<Task>(`/tasks/${id}`),
    enabled: !!id,
  });
}

export function useCreateTask() {
  const token = useAuth((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: any) => request<Task>("/tasks", { method: "POST", body: JSON.stringify(body) }, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });
}

export function useDecideTask() {
  const token = useAuth((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action, note }: { id: string; action: "approve" | "revise" | "reject"; note?: string }) =>
      request<Task>(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify({ action, note }) }, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.invalidateQueries({ queryKey: ["payments"] });
    },
  });
}

// ---- Payments ----
export function usePayments(status?: "pending" | "released" | "disputed") {
  const qs = status ? `?status=${status}` : "";
  return useQuery({
    queryKey: ["payments", status || "all"],
    queryFn: () => request<Payment[]>(`/payments${qs}`),
  });
}
export function usePaymentSummary() {
  return useQuery({
    queryKey: ["payment-summary"],
    queryFn: () => request<{ pending_count: number; pending_total: number; released_total_mtd: number }>("/payments/summary"),
  });
}
export function useBatchRelease() {
  const token = useAuth((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ids: string[]) =>
      request<Payment[]>("/payments/batch-release", { method: "POST", body: JSON.stringify({ ids }) }, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["payments"] });
      qc.invalidateQueries({ queryKey: ["payment-summary"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

// ---- Messages ----
export function useThread(taskId: string | null) {
  return useQuery({
    queryKey: ["thread", taskId],
    queryFn: () => request<Message[]>(`/threads/${taskId}`),
    enabled: !!taskId,
  });
}
export function usePostMessage(taskId: string | null) {
  const token = useAuth((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { body: string; kind?: "user" | "operator" | "system"; attach?: string }) =>
      request<Message>(`/threads/${taskId}`, { method: "POST", body: JSON.stringify(body) }, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["thread", taskId] }),
  });
}
