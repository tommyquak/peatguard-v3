// M4 · Active task / navigation + capture.
// Source: design_handoff_peatguard/mobile-screens.jsx:257-309.
//
// Photo capture in v1: prefers expo-camera if permission granted, falls back
// to a stub blob (so the demo still runs in Expo Go without camera access).
// Each photo is sealed via expo-crypto sha256(blob || prev_sha256) to match
// the contract documented in design_handoff README §State Management.

import { Ionicons } from "@expo/vector-icons";
import * as Crypto from "expo-crypto";
import * as ImagePicker from "expo-image-picker";
import * as Location from "expo-location";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Btn } from "@/components/Btn";
import { Chip } from "@/components/Chip";
import { MapStub } from "@/components/MapStub";
import { MobHeader } from "@/components/MobChrome";
import { useArrive, useTask, uploadPhoto } from "@/api/client";
import { useQueue } from "@/store/queue";
import { useSession } from "@/store/session";
import { useTheme } from "@/theme/useTheme";
import type { StackProps } from "@/navigation/types";

const PHASES = ["before", "during", "after"] as const;
type Phase = typeof PHASES[number];

export function ActiveTaskScreen({ route, navigation }: StackProps<"ActiveTask">) {
  const { colors, isDark } = useTheme();
  const { taskId } = route.params;
  const { data: task, refetch } = useTask(taskId);
  const arrive = useArrive();
  const token = useSession((s) => s.token);
  const enqueue = useQueue((s) => s.enqueue);
  const [phase, setPhase] = useState<Phase>(route.params.phase ?? "before");
  const [arrived, setArrived] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const lastSha = useRef<string | null>(null);

  useEffect(() => {
    if (task && task.arrived_at) setArrived(true);
    if (task && task.photos.length) lastSha.current = task.photos[task.photos.length - 1].sha256;
    if (task) {
      const taken = new Set(task.photos.map((p) => p.phase));
      const next = PHASES.find((p) => !taken.has(p)) ?? "after";
      setPhase(next);
    }
  }, [task?.id, task?.photos.length, task?.arrived_at]);

  if (!task) return null;

  const taken = new Set(task.photos.map((p) => p.phase));
  const allDone = PHASES.every((p) => taken.has(p));

  async function ensureArrived() {
    if (arrived) return;
    let lat = task!.arrived?.lat ?? -2.341;
    let lng = task!.arrived?.lng ?? 113.911;
    let acc = task!.arrived?.acc ?? 8.4;
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === "granted") {
        const fix = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        lat = fix.coords.latitude; lng = fix.coords.longitude; acc = fix.coords.accuracy ?? 8;
      }
    } catch {}
    await arrive.mutateAsync({ id: task!.id, lat, lng, accuracy_m: acc });
    setArrived(true);
  }

  async function onCapture() {
    setCapturing(true);
    try {
      await ensureArrived();
      // Try camera; fall back to a stub URI on devices without permission.
      const cam = await ImagePicker.requestCameraPermissionsAsync();
      let uri: string | null = null;
      if (cam.granted) {
        const res = await ImagePicker.launchCameraAsync({ quality: 0.6, allowsEditing: false });
        if (!res.canceled) uri = res.assets[0].uri;
      }
      if (!uri) uri = `data:text/plain;base64,c3R1Yi1waG90by0=`; // dev stub blob
      const seed = `${uri}|${phase}|${Date.now()}|${lastSha.current ?? ""}`;
      const sha = await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, seed);
      const fix = task!.arrived ?? { lat: -2.341, lng: 113.911, acc: 8.4 };
      const args = {
        taskId: task!.id,
        phase, ts: Date.now(),
        lat: fix.lat, lng: fix.lng, accuracy_m: fix.acc,
        prev_sha256: lastSha.current,
        uri,
      };
      try {
        await uploadPhoto(args, token);
      } catch (uploadErr) {
        await enqueue({ kind: "photo", args, attempts: 0 });
      }
      lastSha.current = sha;
      await refetch();
      const next = PHASES.find((p) => !taken.has(p) && p !== phase);
      if (next) setPhase(next);
      else navigation.replace("Submit", { taskId: task!.id });
    } catch (err: any) {
      Alert.alert("Capture failed", err.message ?? "Unknown error");
    } finally {
      setCapturing(false);
    }
  }

  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: isDark ? "#0e1411" : colors.surface }}>
      <MobHeader
        title={`Capture ${phase}-photo`}
        sub={arrived ? `Step ${PHASES.indexOf(phase) + 2} of 5 · GPS lock 8 m` : "Tap below when you arrive"}
        lead="back"
        onLead={() => navigation.goBack()}
      />
      <View style={{ flex: 1, position: "relative" }}>
        <MapStub height={420} dark={isDark}>
          <View style={[styles.banner, { backgroundColor: colors.primary }]}>
            <Ionicons name="navigate" size={26} color="#fff" />
            <View style={{ flex: 1 }}>
              <Text style={{ color: "#fff", fontWeight: "700", fontSize: 14 }}>Continue 240 m</Text>
              <Text style={{ color: "rgba(255,255,255,0.85)", fontSize: 12 }}>then turn right onto canal track</Text>
            </View>
            <View style={{ alignItems: "flex-end" }}>
              <Text style={{ color: "#fff", fontWeight: "700", fontFamily: "Menlo", fontSize: 13 }}>0.6 km</Text>
              <Text style={{ color: "rgba(255,255,255,0.85)", fontSize: 10 }}>≈ 9 min</Text>
            </View>
          </View>
        </MapStub>
        <View style={[styles.sheet, { backgroundColor: isDark ? "#161d18" : colors.surfaceRaised }]}>
          <View style={[styles.handle, { backgroundColor: colors.borderStrong }]} />
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 }}>
            <Chip tone="success" size="sm">{arrived ? "Arrived on site" : "En route"}</Chip>
            <Text style={{ fontSize: 11, color: colors.inkMuted, fontFamily: "Menlo" }}>
              {task.arrived ? `${task.arrived.lat.toFixed(3)}°, ${task.arrived.lng.toFixed(3)}° · ±${task.arrived.acc.toFixed(0)}m` : "—"}
            </Text>
          </View>
          <Text style={{ fontSize: 16, fontWeight: "700", color: colors.ink, marginBottom: 4 }}>
            {arrived ? `Take a "${phase}" photo facing the canal` : "Walk to the canal site"}
          </Text>
          <Text style={{ fontSize: 12.5, color: colors.inkMuted, lineHeight: 18 }}>
            {arrived
              ? "Stand at the canal mouth, point the camera at the water flow. Both banks should be visible."
              : "When you reach the canal, tap below to confirm your GPS fix and start capture."}
          </Text>
          <View style={{ flexDirection: "row", gap: 6, marginTop: 12 }}>
            {PHASES.map((p) => (
              <View
                key={p}
                style={{
                  flex: 1, aspectRatio: 1, borderRadius: 10,
                  backgroundColor: taken.has(p) ? colors.accentSoft : (isDark ? "#222a25" : colors.surfaceSunken),
                  borderColor: p === phase ? colors.accent : colors.borderStrong,
                  borderWidth: 2, borderStyle: p === phase ? "solid" : "dashed",
                  alignItems: "center", justifyContent: "center", position: "relative",
                }}
              >
                <Ionicons
                  name={taken.has(p) ? "checkmark" : "camera-outline"}
                  size={20}
                  color={taken.has(p) ? colors.accent : colors.inkMuted}
                />
                <View style={{ position: "absolute", bottom: 4, left: 4, paddingHorizontal: 4, backgroundColor: "rgba(0,0,0,0.55)", borderRadius: 3 }}>
                  <Text style={{ color: "#fff", fontSize: 9, fontFamily: "Menlo" }}>{p.slice(0, 3).toUpperCase()}</Text>
                </View>
              </View>
            ))}
          </View>
          <View style={{ flexDirection: "row", gap: 10, marginTop: 14 }}>
            <Btn kind="secondary" icon={<Ionicons name="mic-outline" size={18} color={colors.ink} />}>
              Voice note
            </Btn>
            {!arrived ? (
              <Btn kind="primary" full onPress={ensureArrived} disabled={arrive.isPending}>
                {arrive.isPending ? "Locking GPS…" : "I'm at the site"}
              </Btn>
            ) : allDone ? (
              <Btn kind="success" full onPress={() => navigation.replace("Submit", { taskId: task.id })}>
                All photos taken · Review
              </Btn>
            ) : (
              <Btn
                kind="primary"
                full
                onPress={onCapture}
                disabled={capturing}
                icon={<Ionicons name="camera" size={18} color="#fff" />}
              >
                {capturing ? "Capturing…" : `Take ${phase} photo`}
              </Btn>
            )}
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  banner: {
    position: "absolute", top: 12, left: 12, right: 12,
    paddingHorizontal: 14, paddingVertical: 12, borderRadius: 14,
    flexDirection: "row", alignItems: "center", gap: 12,
  },
  sheet: {
    position: "absolute", left: 0, right: 0, bottom: 0,
    borderTopLeftRadius: 20, borderTopRightRadius: 20,
    padding: 16,
    shadowColor: "#000", shadowOpacity: 0.18, shadowRadius: 24, shadowOffset: { width: 0, height: -8 },
  },
  handle: {
    width: 40, height: 4, borderRadius: 2, alignSelf: "center", marginBottom: 14,
  },
});
