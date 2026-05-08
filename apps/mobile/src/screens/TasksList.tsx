// Tasks tab — flat list of every task in the village (M2 list view alt).

import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import React from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Chip } from "@/components/Chip";
import { MobHeader } from "@/components/MobChrome";
import { useTasks } from "@/api/client";
import { useSession } from "@/store/session";
import { useTheme } from "@/theme/useTheme";
import { formatIDRShort } from "@/lib/format";
import type { RootStackParamList } from "@/navigation/types";
import { Pressable } from "react-native";

const STATUS_TONE: Record<string, "gold" | "info" | "success" | "neutral" | "risk"> = {
  available: "gold",
  accepted: "info",
  submitted: "success",
  approved: "success",
  paid: "neutral",
  rejected: "risk",
};

export function TasksListScreen() {
  const { colors } = useTheme();
  const villageId = useSession((s) => s.villageId);
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { data = [] } = useTasks({ village_id: villageId ?? undefined });

  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.surface }}>
      <MobHeader title="Tasks" sub={`${data.length} in your village`} lead={null} />
      <FlatList
        data={data}
        keyExtractor={(t) => t.id}
        contentContainerStyle={{ padding: 14, gap: 8 }}
        renderItem={({ item }) => (
          <Pressable
            onPress={() => navigation.navigate("TaskDetail", { taskId: item.id })}
            style={[styles.row, { backgroundColor: colors.surfaceRaised, borderColor: colors.border }]}
          >
            <View style={{ flex: 1 }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <Chip size="sm" tone={STATUS_TONE[item.status] ?? "neutral"}>{item.status}</Chip>
                <Text style={{ fontSize: 11, color: colors.inkMuted, fontFamily: "Menlo" }}>{item.id}</Text>
              </View>
              <Text style={{ fontSize: 14, fontWeight: "700", color: colors.ink }}>{item.title}</Text>
              <Text style={{ fontSize: 12, color: colors.inkMuted }}>{item.deadline}</Text>
            </View>
            <Text style={{ fontFamily: "Menlo", fontWeight: "700", color: colors.ink }}>
              {formatIDRShort(item.payout_idr)}
            </Text>
          </Pressable>
        )}
        ListEmptyComponent={
          <Text style={{ color: colors.inkMuted, padding: 24, textAlign: "center" }}>
            No tasks in your village yet.
          </Text>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  row: {
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
});
