// Confirmation after M5 submit. Auto-returns to Map after 2 s.

import { Ionicons } from "@expo/vector-icons";
import React, { useEffect } from "react";
import { Text, View } from "react-native";
import { Btn } from "@/components/Btn";
import { useTask } from "@/api/client";
import { useTheme } from "@/theme/useTheme";
import type { StackProps } from "@/navigation/types";

export function SubmittedScreen({ route, navigation }: StackProps<"Submitted">) {
  const { colors } = useTheme();
  const { taskId } = route.params;
  const { data: task } = useTask(taskId);

  useEffect(() => {
    const t = setTimeout(() => navigation.navigate("Tabs"), 3000);
    return () => clearTimeout(t);
  }, [navigation]);

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center", padding: 32 }}>
      <View style={{ width: 88, height: 88, borderRadius: 44, backgroundColor: colors.accentSoft, alignItems: "center", justifyContent: "center", marginBottom: 24 }}>
        <Ionicons name="checkmark" size={48} color={colors.accent} />
      </View>
      <Text style={{ fontSize: 22, fontWeight: "700", color: colors.ink, textAlign: "center" }}>Submitted</Text>
      <Text style={{ fontSize: 14, color: colors.inkMuted, textAlign: "center", marginTop: 8, lineHeight: 22 }}>
        {task?.title ? `"${task.title}" is in the operator's queue. ` : ""}
        You'll get a push notification when payment is released.
      </Text>
      <Btn kind="primary" full onPress={() => navigation.navigate("Tabs")} style={{ marginTop: 28 }}>
        Back to home
      </Btn>
    </View>
  );
}
