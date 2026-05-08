import { Ionicons } from "@expo/vector-icons";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";
import { useSession } from "@/store/session";
import { useTheme } from "@/theme/useTheme";
import { OnboardingScreen } from "@/screens/Onboarding";
import { HomeScreen } from "@/screens/Home";
import { TaskDetailScreen } from "@/screens/TaskDetail";
import { ActiveTaskScreen } from "@/screens/ActiveTask";
import { SubmitScreen } from "@/screens/Submit";
import { SubmittedScreen } from "@/screens/Submitted";
import { TasksListScreen } from "@/screens/TasksList";
import { EarningsScreen } from "@/screens/Earnings";
import { MessagesScreen } from "@/screens/Messages";
import { ProfileScreen } from "@/screens/Profile";
import type { RootStackParamList, TabsParamList } from "./types";

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tabs = createBottomTabNavigator<TabsParamList>();

function MainTabs() {
  const { colors } = useTheme();
  return (
    <Tabs.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.inkMuted,
        tabBarStyle: { backgroundColor: colors.surfaceRaised, borderTopColor: colors.border },
        tabBarIcon: ({ color, size }) => {
          const m: Record<keyof TabsParamList, keyof typeof Ionicons.glyphMap> = {
            Map: "map-outline",
            Tasks: "list-outline",
            Wallet: "wallet-outline",
            Messages: "chatbubble-ellipses-outline",
            Me: "person-outline",
          };
          return <Ionicons name={m[route.name]} size={size} color={color} />;
        },
      })}
    >
      <Tabs.Screen name="Map" component={HomeScreen} options={{ tabBarLabel: "Map" }} />
      <Tabs.Screen name="Tasks" component={TasksListScreen} options={{ tabBarLabel: "Tasks" }} />
      <Tabs.Screen name="Wallet" component={EarningsScreen} options={{ tabBarLabel: "Wallet" }} />
      <Tabs.Screen name="Messages" component={MessagesScreen} options={{ tabBarLabel: "Messages" }} />
      <Tabs.Screen name="Me" component={ProfileScreen} options={{ tabBarLabel: "Me" }} />
    </Tabs.Navigator>
  );
}

export function RootNavigator() {
  const token = useSession((s) => s.token);
  const villageId = useSession((s) => s.villageId);
  const onboarded = !!token && !!villageId;
  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {!onboarded ? (
          <Stack.Screen name="Onboarding" component={OnboardingScreen} />
        ) : (
          <>
            <Stack.Screen name="Tabs" component={MainTabs} />
            <Stack.Screen name="TaskDetail" component={TaskDetailScreen} />
            <Stack.Screen name="ActiveTask" component={ActiveTaskScreen} />
            <Stack.Screen name="Submit" component={SubmitScreen} />
            <Stack.Screen name="Submitted" component={SubmittedScreen} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
