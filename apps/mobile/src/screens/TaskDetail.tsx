// M3 · Task detail.
// Source: design_handoff_peatguard/mobile-screens.jsx:188-254.

import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Alert, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Btn } from "@/components/Btn";
import { Card } from "@/components/Card";
import { Chip } from "@/components/Chip";
import { MapStub } from "@/components/MapStub";
import { MobHeader } from "@/components/MobChrome";
import { useAcceptTask, useTask } from "@/api/client";
import { useTheme } from "@/theme/useTheme";
import { formatIDRShort } from "@/lib/format";
import type { StackProps } from "@/navigation/types";

export function TaskDetailScreen({ route, navigation }: StackProps<"TaskDetail">) {
  const { colors } = useTheme();
  const { taskId } = route.params;
  const { data: task } = useTask(taskId);
  const accept = useAcceptTask();

  if (!task) return null;
  const sub = task.sub ?? task.aoi_code;

  async function onAccept() {
    if (!task) return;
    try {
      await accept.mutateAsync(task.id);
      navigation.navigate("ActiveTask", { taskId: task.id, phase: "before" });
    } catch (err: any) {
      Alert.alert("Could not accept", err.message ?? "Unknown error");
    }
  }

  const accepted = task.status !== "available";

  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.surface }}>
      <MobHeader
        title={task.title}
        sub={sub}
        lead="back"
        onLead={() => navigation.goBack()}
      />
      <ScrollView contentContainerStyle={{ paddingBottom: 24 }}>
        <View style={{ height: 200, position: "relative" }}>
          <MapStub height={200}>
            <View style={{ position: "absolute", top: 10, right: 10, paddingHorizontal: 8, paddingVertical: 4, backgroundColor: "rgba(255,255,255,0.9)", borderRadius: 6 }}>
              <Text style={{ fontSize: 10.5, fontFamily: "Menlo" }}>−2.341°S · 113.91°E</Text>
            </View>
          </MapStub>
        </View>
        <View style={{ padding: 18, gap: 14 }}>
          <View style={{ flexDirection: "row", alignItems: "flex-end", justifyContent: "space-between", gap: 10 }}>
            <View style={{ flex: 1 }}>
              <Chip tone={task.status === "available" ? "gold" : "info"} size="sm">
                {task.status[0].toUpperCase() + task.status.slice(1)}
              </Chip>
              <Text style={{ fontSize: 22, fontWeight: "700", letterSpacing: -0.5, marginTop: 8, color: colors.ink }}>
                {task.title}
              </Text>
              <Text style={{ fontSize: 12, color: colors.inkMuted, marginTop: 2 }}>
                Deadline: {task.deadline}
              </Text>
            </View>
            <View style={{ alignItems: "flex-end" }}>
              <Text style={{ fontSize: 11, color: colors.inkMuted, textTransform: "uppercase", fontWeight: "700" }}>Pay</Text>
              <Text style={{ fontSize: 22, fontWeight: "700", fontFamily: "Menlo", color: colors.ink }}>
                {formatIDRShort(task.payout_idr)}
              </Text>
            </View>
          </View>

          <Card>
            <Text style={[styles.sectionTitle, { color: colors.ink }]}>What to do</Text>
            <Steps items={[
              "Bring dam materials (sandbags, timber) to the canal point.",
              "Build the dam across the canal mouth, at least 8 m wide.",
              "Wait until water rises on the upstream side (≈ 2 hours).",
              "Take photos: before, during, and after.",
            ]} />
          </Card>

          <Card pad={0} style={{ overflow: "hidden" }}>
            <View style={{ paddingHorizontal: 14, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.border }}>
              <Text style={[styles.sectionTitle, { color: colors.ink }]}>Examples of accepted work</Text>
            </View>
            <View style={{ flexDirection: "row" }}>
              {[1, 2, 3].map((i) => (
                <View
                  key={i}
                  style={{
                    flex: 1, aspectRatio: 1, backgroundColor: colors.surfaceSunken,
                    borderRightWidth: i < 3 ? 1 : 0, borderColor: colors.border,
                    alignItems: "center", justifyContent: "center",
                  }}
                >
                  <Ionicons name="image-outline" size={28} color={colors.inkMuted} />
                </View>
              ))}
            </View>
          </Card>

          <Card>
            <Text style={[styles.sectionTitle, { color: colors.ink, marginBottom: 8 }]}>Required deliverables</Text>
            {(task.deliverables.length ? task.deliverables : ["3 photos: before, during, after", "GPS track of dam (≥ 8 m)"]).map((d) => (
              <View key={d} style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 6 }}>
                <View style={{ width: 18, height: 18, borderRadius: 9, backgroundColor: colors.accentSoft, alignItems: "center", justifyContent: "center" }}>
                  <Ionicons name="checkmark" size={11} color={colors.accent} />
                </View>
                <Text style={{ flex: 1, fontSize: 13, color: colors.ink }}>{d}</Text>
              </View>
            ))}
          </Card>

          <View style={{ padding: 12, backgroundColor: colors.primarySoft, borderRadius: 10, flexDirection: "row", gap: 10 }}>
            <Ionicons name="shield-checkmark" size={16} color={colors.primary} style={{ marginTop: 2 }} />
            <View style={{ flex: 1 }}>
              <Text style={{ color: colors.primary, fontSize: 12, lineHeight: 17 }}>
                <Text style={{ fontWeight: "700" }}>Payment is secured.</Text> Once the operator approves your photos, money lands in your DANA wallet in ≈ 1 minute.
              </Text>
            </View>
          </View>
        </View>
      </ScrollView>
      <View style={{ padding: 16, paddingTop: 12, backgroundColor: colors.surfaceRaised, borderTopWidth: 1, borderTopColor: colors.border, flexDirection: "row", gap: 10 }}>
        <Btn kind="secondary" icon={<Ionicons name="chatbubble-outline" size={18} color={colors.ink} />}>
          Ask
        </Btn>
        {accepted ? (
          <Btn kind="success" full onPress={() => navigation.navigate("ActiveTask", { taskId: task.id, phase: "before" })}>
            Continue task
          </Btn>
        ) : (
          <Btn kind="primary" full onPress={onAccept} disabled={accept.isPending}>
            {accept.isPending ? "Accepting…" : `Accept · ${formatIDRShort(task.payout_idr)}`}
          </Btn>
        )}
      </View>
    </SafeAreaView>
  );
}

function Steps({ items }: { items: string[] }) {
  const { colors } = useTheme();
  return (
    <View>
      {items.map((it, i) => (
        <View key={i} style={{ flexDirection: "row", gap: 10, paddingVertical: 4 }}>
          <Text style={{ fontFamily: "Menlo", color: colors.inkMuted, width: 18 }}>{i + 1}.</Text>
          <Text style={{ flex: 1, fontSize: 13, lineHeight: 20, color: colors.ink }}>{it}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  sectionTitle: { fontSize: 12.5, fontWeight: "700" },
});
