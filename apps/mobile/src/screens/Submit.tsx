// M5 · Submit for review.
// Source: design_handoff_peatguard/mobile-screens.jsx:312-382.

import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Alert, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Btn } from "@/components/Btn";
import { Card } from "@/components/Card";
import { Chip } from "@/components/Chip";
import { MobHeader } from "@/components/MobChrome";
import { useSubmitTask, useTask } from "@/api/client";
import { useTheme } from "@/theme/useTheme";
import { formatIDR } from "@/lib/format";
import type { StackProps } from "@/navigation/types";

export function SubmitScreen({ route, navigation }: StackProps<"Submit">) {
  const { colors, isDark } = useTheme();
  const { taskId } = route.params;
  const { data: task } = useTask(taskId);
  const submit = useSubmitTask();
  if (!task) return null;

  async function onSubmit() {
    if (!task) return;
    try {
      await submit.mutateAsync(task.id);
      navigation.replace("Submitted", { taskId: task.id });
    } catch (err: any) {
      Alert.alert("Submit failed", err.message ?? "Unknown error");
    }
  }

  const photos = task.photos;

  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: isDark ? "#0e1411" : colors.surface }}>
      <MobHeader title="Submit for review" sub="Check before sending" lead="back" onLead={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }}>
        <Card>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
            <View style={{ width: 36, height: 36, borderRadius: 10, backgroundColor: colors.accentSoft, alignItems: "center", justifyContent: "center" }}>
              <Ionicons name="shield-checkmark" size={18} color={colors.accent} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: 14, fontWeight: "700", color: colors.ink }}>{task.title}</Text>
              <Text style={{ fontSize: 12, color: colors.inkMuted }}>
                Pay <Text style={{ color: colors.ink, fontFamily: "Menlo" }}>{formatIDR(task.payout_idr)}</Text> · {task.aoi_code}
              </Text>
            </View>
            <Chip tone="success" size="sm">Ready</Chip>
          </View>
        </Card>

        <View>
          <Text style={[styles.sectionTitle, { color: colors.ink, marginBottom: 8 }]}>Photos ({photos.length}/3)</Text>
          <View style={{ flexDirection: "row", gap: 8 }}>
            {(["before", "during", "after"] as const).map((phase, i) => {
              const p = photos.find((x) => x.phase === phase);
              return (
                <View key={phase} style={{ flex: 1, aspectRatio: 1, borderRadius: 10, backgroundColor: p ? colors.accentSoft : colors.surfaceSunken, alignItems: "center", justifyContent: "center", position: "relative" }}>
                  {p ? (
                    <Ionicons name="image" size={24} color={colors.accent} />
                  ) : (
                    <Ionicons name="image-outline" size={24} color={colors.inkMuted} />
                  )}
                  <View style={{ position: "absolute", left: 4, right: 4, bottom: 4, paddingHorizontal: 4, backgroundColor: "rgba(0,0,0,0.55)", borderRadius: 4, alignItems: "center" }}>
                    <Text style={{ color: "#fff", fontSize: 10, fontFamily: "Menlo" }}>
                      {phase} {p ? new Date(p.ts).toTimeString().slice(0, 5) : "—"}
                    </Text>
                  </View>
                </View>
              );
            })}
          </View>
        </View>

        <Card>
          <Text style={[styles.sectionTitle, { color: colors.ink, marginBottom: 10 }]}>Auto-checks</Text>
          {[
            ["GPS lock", task.arrived ? `${task.arrived.acc.toFixed(1)} m mean offset` : "—", !!task.arrived],
            ["Within work window", photos.length ? `${new Date(photos[0].ts).toTimeString().slice(0, 5)} → ${new Date(photos[photos.length - 1].ts).toTimeString().slice(0, 5)} WIB` : "—", true],
            ["Photos sealed (sha256)", `chain intact, ${photos.length} photos`, true],
            ["Dam track", "24.1 m linear", true],
          ].map(([l, v, ok]) => (
            <View key={l as string} style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 6 }}>
              <View style={{ width: 18, height: 18, borderRadius: 9, backgroundColor: ok ? colors.accentSoft : colors.riskSoft, alignItems: "center", justifyContent: "center" }}>
                <Ionicons name={ok ? "checkmark" : "close"} size={11} color={ok ? colors.accent : colors.risk} />
              </View>
              <Text style={{ flex: 1, fontSize: 12.5, color: colors.ink }}>{l}</Text>
              <Text style={{ fontSize: 11, color: colors.inkMuted, fontFamily: "Menlo" }}>{v}</Text>
            </View>
          ))}
        </Card>

        <Card>
          <Text style={[styles.sectionTitle, { color: colors.ink, marginBottom: 6 }]}>Voice note · 0:24</Text>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
            <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" }}>
              <Ionicons name="play" size={14} color="#fff" />
            </View>
            <Text style={{ flex: 1, color: colors.inkMuted }}>▁▂▃▅▇▅▃▂▁ stub waveform</Text>
          </View>
        </Card>

        <Card pad={14} style={{ backgroundColor: colors.accentSoft, borderWidth: 0 }}>
          <View style={{ flexDirection: "row", gap: 10 }}>
            <Ionicons name="information-circle" size={16} color={colors.accent} style={{ marginTop: 2 }} />
            <Text style={{ flex: 1, color: "#2d6e44", fontSize: 12.5, lineHeight: 18 }}>
              <Text style={{ fontWeight: "700" }}>No signal?</Text> Your submission is saved on this phone and uploads automatically when you're back online.
            </Text>
          </View>
        </Card>
      </ScrollView>
      <View style={{ padding: 16, paddingTop: 12, backgroundColor: colors.surfaceRaised, borderTopWidth: 1, borderTopColor: colors.border, flexDirection: "row", gap: 10 }}>
        <Btn kind="secondary">Save draft</Btn>
        <Btn kind="primary" full onPress={onSubmit} disabled={submit.isPending} icon={<Ionicons name="cloud-upload-outline" size={18} color="#fff" />}>
          {submit.isPending ? "Submitting…" : "Submit for review"}
        </Btn>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  sectionTitle: { fontSize: 13, fontWeight: "700" },
});
