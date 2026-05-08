import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { BottomTabScreenProps } from "@react-navigation/bottom-tabs";

export type RootStackParamList = {
  Onboarding: undefined;
  Tabs: undefined;
  TaskDetail: { taskId: string };
  ActiveTask: { taskId: string; phase?: "before" | "during" | "after" };
  Submit: { taskId: string };
  Submitted: { taskId: string };
};

export type TabsParamList = {
  Map: undefined;
  Tasks: undefined;
  Wallet: undefined;
  Messages: undefined;
  Me: undefined;
};

export type StackProps<T extends keyof RootStackParamList> = NativeStackScreenProps<RootStackParamList, T>;
export type TabProps<T extends keyof TabsParamList> = BottomTabScreenProps<TabsParamList, T>;
