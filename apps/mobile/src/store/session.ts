import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import type { User } from "@/api/types";

const KEY = "pg-session";

interface SessionState {
  token: string | null;
  user: User | null;
  villageId: string | null;
  villageName: string | null;
  workerId: string | null;
  hydrated: boolean;
  hydrate: () => Promise<void>;
  setSession: (token: string, user: User) => Promise<void>;
  setVillage: (id: string, name: string) => Promise<void>;
  setWorker: (id: string) => Promise<void>;
  clear: () => Promise<void>;
}

export const useSession = create<SessionState>((set) => ({
  token: null,
  user: null,
  villageId: null,
  villageName: null,
  workerId: null,
  hydrated: false,
  hydrate: async () => {
    const raw = await AsyncStorage.getItem(KEY);
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        set({ ...parsed, hydrated: true });
        return;
      } catch {}
    }
    set({ hydrated: true });
  },
  setSession: async (token, user) => {
    set({ token, user });
    await persist();
  },
  setVillage: async (id, name) => {
    set({ villageId: id, villageName: name });
    await persist();
  },
  setWorker: async (id) => {
    set({ workerId: id });
    await persist();
  },
  clear: async () => {
    await AsyncStorage.removeItem(KEY);
    set({ token: null, user: null, villageId: null, villageName: null, workerId: null });
  },
}));

async function persist() {
  const s = useSession.getState();
  await AsyncStorage.setItem(KEY, JSON.stringify({
    token: s.token, user: s.user, villageId: s.villageId, villageName: s.villageName, workerId: s.workerId,
  }));
}
