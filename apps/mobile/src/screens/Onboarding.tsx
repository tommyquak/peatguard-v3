// M1 · Onboarding.
// Source: design_handoff_peatguard/mobile-screens.jsx:54-93.

import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Btn } from "@/components/Btn";
import { Logomark } from "@/components/Logomark";
import { useVillagerLogin, useVillages } from "@/api/client";
import { useSession } from "@/store/session";
import { useTheme } from "@/theme/useTheme";

export function OnboardingScreen() {
  const { colors } = useTheme();
  const villages = useVillages().data ?? [];
  const login = useVillagerLogin();
  const setVillage = useSession((s) => s.setVillage);
  const setWorker = useSession((s) => s.setWorker);
  const [phone, setPhone] = useState("+62812 4218");
  const [villageId, setVillageId] = useState<string | null>(null);

  React.useEffect(() => {
    if (!villageId && villages.length) setVillageId(villages[0].id);
  }, [villageId, villages.length]);

  async function onContinue() {
    try {
      // Sumardi is the demo worker; assigning him so existing fixtures (C-02 submission etc.) light up.
      await login.mutateAsync({ phone: phone || "w-sumardi" });
      const v = villages.find((v) => v.id === villageId);
      if (v) await setVillage(v.id, v.name);
      await setWorker("w-sumardi");
    } catch (err: any) {
      Alert.alert("Sign-in failed", err.message ?? "Unknown error");
    }
  }

  return (
    <SafeAreaView edges={["top", "bottom"]} style={{ flex: 1, backgroundColor: colors.surface }}>
      <ScrollView contentContainerStyle={{ padding: 24, paddingTop: 32 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 28 }}>
          <Logomark size={32} />
          <Text style={[styles.brand, { color: colors.ink }]}>PeatGuard</Text>
        </View>
        <View style={[styles.hero, { backgroundColor: colors.surfaceSunken }]}>
          <Logomark size={64} />
          <Text style={[styles.heroSub, { color: colors.inkMuted }]}>peatland · sentinel-1 · IDR</Text>
        </View>
        <Text style={[styles.title, { color: colors.ink }]}>
          Peat protection work. Transparent pay.
        </Text>
        <Text style={[styles.subtitle, { color: colors.inkSecondary }]}>
          Restoration work in your village. Photos prove it. PeatGuard pays you within minutes after the operator approves.
        </Text>

        <View style={{ marginTop: 22, gap: 10 }}>
          <Step
            n={1}
            title="Choose language"
            value="English · Bahasa · Dayak Ngaju"
            done
          />
          <Step
            n={2}
            title="Phone number & OTP"
            value={
              <TextInput
                value={phone}
                onChangeText={setPhone}
                placeholder="+62..."
                style={[styles.input, { color: colors.ink, borderColor: colors.border }]}
              />
            }
          />
          <Step
            n={3}
            title="Pick your village"
            value={
              <View style={{ gap: 6, marginTop: 4 }}>
                {villages.map((v) => (
                  <Btn
                    key={v.id}
                    kind={v.id === villageId ? "soft" : "ghost"}
                    size="sm"
                    onPress={() => setVillageId(v.id)}
                    full
                    style={{ justifyContent: "flex-start" }}
                  >
                    {`${v.name}${v.id === villageId ? " · selected" : ""}`}
                  </Btn>
                ))}
              </View>
            }
            active
          />
          <Step
            n={4}
            title="ID verification (NIK + selfie)"
            value="Optional · unlocks higher payouts"
          />
        </View>
      </ScrollView>
      <View style={{ padding: 16, gap: 10 }}>
        <Btn kind="primary" full onPress={onContinue} disabled={login.isPending || !villageId}>
          {login.isPending ? "Signing in…" : "Continue"}
        </Btn>
        <Btn kind="ghost" full onPress={onContinue}>Skip for now</Btn>
      </View>
    </SafeAreaView>
  );
}

function Step({
  n, title, value, done, active,
}: {
  n: number;
  title: string;
  value: React.ReactNode;
  done?: boolean;
  active?: boolean;
}) {
  const { colors } = useTheme();
  return (
    <View
      style={{
        padding: 14,
        borderRadius: 12,
        backgroundColor: active ? colors.primarySoft : colors.surfaceRaised,
        borderColor: active ? colors.primary : colors.border,
        borderWidth: 1,
        flexDirection: "row",
        alignItems: "center",
        gap: 12,
      }}
    >
      <View
        style={{
          width: 28, height: 28, borderRadius: 14,
          backgroundColor: done ? colors.accent : active ? colors.primary : colors.surfaceSunken,
          alignItems: "center", justifyContent: "center",
        }}
      >
        {done ? (
          <Ionicons name="checkmark" size={14} color="#fff" />
        ) : (
          <Text style={{ color: active ? "#fff" : colors.inkMuted, fontSize: 12, fontWeight: "700" }}>{n}</Text>
        )}
      </View>
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={{ fontSize: 13.5, fontWeight: "600", color: colors.ink }}>{title}</Text>
        {typeof value === "string" ? (
          <Text style={{ fontSize: 11.5, color: colors.inkMuted }}>{value}</Text>
        ) : (
          value
        )}
      </View>
      {done && <Ionicons name="checkmark" size={16} color={colors.accent} />}
      {active && <Ionicons name="chevron-forward" size={16} color={colors.primary} />}
    </View>
  );
}

const styles = StyleSheet.create({
  brand: { fontSize: 17, fontWeight: "700" },
  hero: {
    width: "100%", aspectRatio: 4 / 3, borderRadius: 14,
    marginBottom: 24, alignItems: "center", justifyContent: "center", gap: 8,
  },
  heroSub: { fontSize: 11, fontFamily: "Menlo" },
  title: { fontSize: 26, fontWeight: "700", letterSpacing: -0.5, lineHeight: 30 },
  subtitle: { fontSize: 14, marginTop: 10, lineHeight: 21 },
  input: {
    borderWidth: 1, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6,
    fontSize: 13, marginTop: 4, backgroundColor: "#fff",
  },
});
