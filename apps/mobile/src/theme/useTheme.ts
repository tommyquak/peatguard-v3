import { useColorScheme } from "react-native";
import { colorsDark, colorsLight, type Palette } from "./colors";

export interface Theme {
  colors: Palette;
  isDark: boolean;
}

export function useTheme(forceDark?: boolean): Theme {
  const scheme = useColorScheme();
  const isDark = forceDark ?? scheme === "dark";
  return { colors: isDark ? colorsDark : colorsLight, isDark };
}
