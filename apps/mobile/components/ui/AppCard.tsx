import { StyleSheet, View, ViewProps } from 'react-native';
import { COLORS, RADIUS, SPACE, SHADOW } from '@/lib/theme';

interface AppCardProps extends ViewProps {
  variant?: 'dark' | 'light';
}

export function AppCard({ variant = 'dark', style, children, ...props }: AppCardProps) {
  return (
    <View style={[styles.base, VARIANT[variant], style]} {...props}>
      {children}
    </View>
  );
}

const VARIANT = {
  dark:  { backgroundColor: COLORS.dark.surface },
  light: { backgroundColor: COLORS.light.surface, borderWidth: 1, borderColor: COLORS.light.border, ...SHADOW.card },
};

const styles = StyleSheet.create({
  base: { padding: SPACE.lg + 2, borderRadius: RADIUS.lg, marginBottom: SPACE.md },
});
