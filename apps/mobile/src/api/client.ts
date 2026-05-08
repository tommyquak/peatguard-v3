import Constants from "expo-constants";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "@/store/session";
import type {
  Aoi,
  Message,
  Payment,
  Task,
  TaskStatus,
  User,
  Village,
} from "./types";

export const API_BASE: string =
  (Constants.expoConfig?.extra as any)?.apiBase || "http://localhost:8080";

async function request<T>(path: string, init: RequestInit = {}, token?: string | null): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) {
    let detail: string | undefined;
    try { detail = (await res.json()).detail; } catch {}
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ---- Auth ----
export function useVillagerLogin() {
  const setSession = useSession((s) => s.setSession);
  return useMutation({
    mutationFn: async (vars: { phone: string }) => {
      const data = await request<{ token: string; user: User }>(
        "/auth/villager-login",
        { method: "POST", body: JSON.stringify({ email: vars.phone, password: "x" }) },
      );
      await setSession(data.token, data.user);
      return data;
    },
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
    refetchInterval: 30_000,
  });
}

export function useTask(id: string | null) {
  return useQuery({
    queryKey: ["task", id],
    queryFn: () => request<Task>(`/tasks/${id}`),
    enabled: !!id,
  });
}

export function useAcceptTask() {
  const token = useSession((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => request<Task>(`/tasks/${id}/accept`, { method: "POST" }, token),
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.setQueryData(["task", t.id], t);
    },
  });
}

export function useArrive() {
  const token = useSession((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, lat, lng, accuracy_m }: { id: string; lat: number; lng: number; accuracy_m: number }) =>
      request<Task>(`/tasks/${id}/arrive`, {
        method: "POST",
        body: JSON.stringify({ lat, lng, accuracy_m }),
      }, token),
    onSuccess: (t) => {
      qc.setQueryData(["task", t.id], t);
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export interface UploadPhotoArgs {
  taskId: string;
  phase: "before" | "during" | "after";
  ts: number;
  lat: number;
  lng: number;
  accuracy_m: number;
  prev_sha256: string | null;
  uri: string;
}

export async function uploadPhoto(args: UploadPhotoArgs, token: string | null): Promise<Task> {
  const form = new FormData();
  form.append("phase", args.phase);
  form.append("ts", String(args.ts));
  form.append("lat", String(args.lat));
  form.append("lng", String(args.lng));
  form.append("accuracy_m", String(args.accuracy_m));
  if (args.prev_sha256) form.append("prev_sha256", args.prev_sha256);
  // RN FormData file shape:
  form.append("blob", {
    uri: args.uri,
    name: `${args.phase}.jpg`,
    type: "image/jpeg",
  } as any);
  const res = await fetch(`${API_BASE}/api/v1/tasks/${args.taskId}/photos`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) {
    let detail: string | undefined;
    try { detail = (await res.json()).detail; } catch {}
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export function useSubmitTask() {
  const token = useSession((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => request<Task>(`/tasks/${id}/submit`, { method: "POST" }, token),
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.setQueryData(["task", t.id], t);
    },
  });
}

// ---- Aux ----
export function useAois() { return useQuery({ queryKey: ["aois"], queryFn: () => request<Aoi[]>("/aois") }); }
export function useVillages() { return useQuery({ queryKey: ["villages"], queryFn: () => request<Village[]>("/villages") }); }
export function usePayments(workerId: string | null) {
  return useQuery({
    queryKey: ["payments", workerId],
    queryFn: async () => {
      const all = await request<Payment[]>("/payments");
      return workerId ? all.filter((p) => p.worker_id === workerId) : all;
    },
  });
}

export function useThread(taskId: string | null) {
  return useQuery({
    queryKey: ["thread", taskId],
    queryFn: () => request<Message[]>(`/threads/${taskId}`),
    enabled: !!taskId,
  });
}
export function usePostMessage(taskId: string | null) {
  const token = useSession((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { body: string; attach?: string }) =>
      request<Message>(`/threads/${taskId}`, { method: "POST", body: JSON.stringify({ ...body, kind: "user" }) }, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["thread", taskId] }),
  });
}

export { request };
