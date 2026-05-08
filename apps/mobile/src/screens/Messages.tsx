// M7 · Notifications + messages.
// Source: design_handoff_peatguard/mobile-screens.jsx:439-490.

import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { MobHeader } from "@/components/MobChrome";
import { usePostMessage, useTasks, useThread } from "@/api/client";
import { useSession } from "@/store/session";
import { useTheme } from "@/theme/useTheme";

export function MessagesScreen() {
  const { colors } = useTheme();
  const workerId = useSession((s) => s.workerId);
  const { data: tasks = [] } = useTasks({ worker_id: workerId ?? undefined });
  const [activeId, setActiveId] = useState<string | null>(null);
  useEffect(() => {
    if (!activeId && tasks.length) setActiveId(tasks[0].id);
  }, [activeId, tasks.length]);

  const thread = useThread(activeId);
  const post = usePostMessage(activeId);
  const [draft, setDraft] = useState("");

  async function send() {
    if (!draft.trim()) return;
    try {
      await post.mutateAsync({ body: draft.trim() });
      setDraft("");
    } catch {}
  }

  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.surface }}>
      <MobHeader title="Messages" sub="Operator · System" lead={null} />
      <View style={{ paddingHorizontal: 16, paddingTop: 16, paddingBottom: 8, backgroundColor: colors.primarySoft, borderBottomWidth: 1, borderBottomColor: colors.border }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
          <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" }}>
            <Text style={{ color: "#fff", fontWeight: "700", fontSize: 12 }}>NA</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: 14, fontWeight: "700", color: colors.ink }}>Nadia · PeatGuard operator</Text>
            <Text style={{ fontSize: 11, color: colors.inkMuted }}>Online · usually replies within an hour</Text>
          </View>
        </View>
        {tasks.length > 1 && (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 10 }} contentContainerStyle={{ gap: 6 }}>
            {tasks.map((t) => (
              <Pressable
                key={t.id}
                onPress={() => setActiveId(t.id)}
                style={{
                  paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999,
                  backgroundColor: t.id === activeId ? colors.primary : "transparent",
                  borderWidth: 1, borderColor: t.id === activeId ? colors.primary : colors.border,
                }}
              >
                <Text style={{ color: t.id === activeId ? "#fff" : colors.inkSecondary, fontSize: 11, fontWeight: "600" }}>
                  {t.id}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        )}
      </View>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 10 }}>
        {(thread.data ?? []).map((m) => (
          <Bubble key={m.id} side={m.kind === "user" ? "me" : m.kind === "system" ? "sys" : "them"} body={m.body} attach={m.attach} />
        ))}
        {!thread.data?.length && (
          <Text style={{ color: colors.inkMuted, padding: 16, textAlign: "center" }}>No messages yet.</Text>
        )}
      </ScrollView>
      <View style={{ paddingHorizontal: 12, paddingVertical: 10, backgroundColor: colors.surfaceRaised, borderTopWidth: 1, borderTopColor: colors.border, flexDirection: "row", alignItems: "center", gap: 8 }}>
        <Pressable style={{ width: 38, height: 38, borderRadius: 19, backgroundColor: colors.surfaceSunken, alignItems: "center", justifyContent: "center" }}>
          <Ionicons name="add" size={18} color={colors.ink} />
        </Pressable>
        <TextInput
          value={draft}
          onChangeText={setDraft}
          placeholder="Type a message…"
          placeholderTextColor={colors.inkMuted}
          style={{ flex: 1, height: 38, paddingHorizontal: 14, borderRadius: 19, backgroundColor: colors.surfaceSunken, fontSize: 13, color: colors.ink }}
        />
        <Pressable onPress={send} style={{ width: 38, height: 38, borderRadius: 19, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" }}>
          <Ionicons name={draft ? "send" : "mic"} size={18} color="#fff" />
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

function Bubble({ side, body, attach }: { side: "me" | "them" | "sys"; body: string; attach: string | null }) {
  const { colors } = useTheme();
  if (side === "sys") {
    return (
      <View style={{ alignSelf: "center", maxWidth: "85%", paddingHorizontal: 14, paddingVertical: 10, backgroundColor: colors.accentSoft, borderRadius: 12, flexDirection: "row", gap: 8, alignItems: "center" }}>
        <Ionicons name="checkmark-circle" size={14} color={colors.accent} />
        <Text style={{ color: "#2d6e44", fontSize: 12.5 }}>{body}</Text>
      </View>
    );
  }
  const me = side === "me";
  return (
    <View style={{ alignSelf: me ? "flex-end" : "flex-start", maxWidth: "78%", gap: 4 }}>
      {attach && (
        <View style={{ width: 140, aspectRatio: 4 / 3, borderRadius: 10, backgroundColor: colors.surfaceSunken, alignItems: "center", justifyContent: "center" }}>
          <Ionicons name="image-outline" size={28} color={colors.inkMuted} />
        </View>
      )}
      {body ? (
        <View
          style={{
            paddingHorizontal: 13, paddingVertical: 9,
            backgroundColor: me ? colors.primary : colors.surfaceRaised,
            borderColor: me ? "transparent" : colors.border,
            borderWidth: 1,
            borderRadius: 14,
            borderBottomRightRadius: me ? 4 : 14,
            borderBottomLeftRadius: me ? 14 : 4,
          }}
        >
          <Text style={{ color: me ? "#fff" : colors.ink, fontSize: 13, lineHeight: 19 }}>{body}</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({});
