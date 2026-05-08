import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StatusBar } from "expo-status-bar";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { i18next } from "@/i18n";
import { RootNavigator } from "@/navigation/RootNavigator";
import { useSession } from "@/store/session";
import { useQueue, watchNetwork } from "@/store/queue";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } },
});

export default function App() {
  const hydrate = useSession((s) => s.hydrate);
  const hydrated = useSession((s) => s.hydrated);
  const token = useSession((s) => s.token);
  const loadQueue = useQueue((s) => s.load);
  const drain = useQueue((s) => s.drain);

  useEffect(() => {
    hydrate();
    loadQueue();
  }, []);

  useEffect(() => {
    return watchNetwork(() => {
      drain(token).catch(() => {});
    });
  }, [token]);

  // Quiet warning about i18next not being used; the import has the side
  // effect of initialising it.
  useEffect(() => { void i18next.t("app"); }, []);

  if (!hydrated) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#1f4d3a" }}>
        <ActivityIndicator color="#fff" />
      </View>
    );
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <RootNavigator />
          <StatusBar style="auto" />
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
