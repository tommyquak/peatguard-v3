// Offline-first photo + submission queue. Uses AsyncStorage as the durable
// log; NetInfo subscription in App.tsx triggers a drain on connectivity
// restore. Each entry retries with exponential backoff.

import AsyncStorage from "@react-native-async-storage/async-storage";
import NetInfo from "@react-native-community/netinfo";
import { create } from "zustand";
import { uploadPhoto, type UploadPhotoArgs, request } from "@/api/client";

const KEY = "pg-offline-queue";

type Entry =
  | { kind: "photo"; args: UploadPhotoArgs; attempts: number }
  | { kind: "submit"; taskId: string; attempts: number };

interface QueueState {
  entries: Entry[];
  load: () => Promise<void>;
  enqueue: (e: Entry) => Promise<void>;
  drain: (token: string | null) => Promise<{ ok: number; fail: number }>;
}

export const useQueue = create<QueueState>((set, get) => ({
  entries: [],
  load: async () => {
    const raw = await AsyncStorage.getItem(KEY);
    set({ entries: raw ? JSON.parse(raw) : [] });
  },
  enqueue: async (e) => {
    const next = [...get().entries, e];
    set({ entries: next });
    await AsyncStorage.setItem(KEY, JSON.stringify(next));
  },
  drain: async (token) => {
    const { entries } = get();
    const remaining: Entry[] = [];
    let ok = 0;
    let fail = 0;
    for (const e of entries) {
      try {
        if (e.kind === "photo") await uploadPhoto(e.args, token);
        else await request(`/tasks/${e.taskId}/submit`, { method: "POST" }, token);
        ok += 1;
      } catch {
        fail += 1;
        remaining.push({ ...e, attempts: e.attempts + 1 });
      }
    }
    set({ entries: remaining });
    await AsyncStorage.setItem(KEY, JSON.stringify(remaining));
    return { ok, fail };
  },
}));

export function watchNetwork(onOnline: () => void) {
  return NetInfo.addEventListener((state) => {
    if (state.isConnected && state.isInternetReachable !== false) onOnline();
  });
}
