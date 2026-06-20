import { ActivityIndicator, Pressable, PressableProps, StyleProp, StyleSheet, Text, ViewStyle } from 'react-native';
import { COLORS, RADIUS, SHADOW } from '@/lib/theme';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';
type Size    = 'sm' | 'md' | 'lg';

interface AppButtonProps extends Omit<PressableProps, 'style'> {
  variant?: Variant;
  size?:    Size;
  loading?: boolean;
  children: React.ReactNode;
  style?:   StyleProp<ViewStyle>;
}

export function AppButton({
  variant = 'primary',
  size    = 'md',
  loading,
  disabled,
  children,
  style,
  ...props
}: AppButtonProps) {
  return (
    <Pressable
      {...props}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.base,
        SIZE[size],
        VARIANT[variant].btn,
        variant === 'primary' && SHADOW.primary,
        (disabled || loading) && styles.disabled,
        pressed && !(disabled || loading) && styles.pressed,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variant === 'primary' ? '#fff' : COLORS.primary} />
      ) : (
        <Text style={[styles.text, SIZE_TEXT[size], VARIANT[variant].text]}>
          {children}
        </Text>
      )}
    </Pressable>
  );
}

const VARIANT: Record<Variant, { btn: object; text: object }> = {
  primary:   { btn: { backgroundColor: COLORS.primary },                                                             text: { color: '#FFFFFF' } },
  secondary: { btn: { backgroundColor: 'transparent', borderWidth: 1, borderColor: COLORS.light.border },            text: { color: COLORS.light.textSecondary } },
  danger:    { btn: { backgroundColor: COLORS.dark.surfaceAlt },                                                     text: { color: COLORS.error } },
  ghost:     { btn: { backgroundColor: 'transparent' },                                                              text: { color: COLORS.primary } },
};

const SIZE: Record<Size, object> = {
  sm: { paddingVertical: 10, borderRadius: RADIUS.md },
  md: { paddingVertical: 14, borderRadius: RADIUS.lg },
  lg: { paddingVertical: 17, borderRadius: RADIUS.lg },
};

const SIZE_TEXT: Record<Size, object> = {
  sm: { fontSize: 13 },
  md: { fontSize: 15 },
  lg: { fontSize: 16 },
};

const styles = StyleSheet.create({
  base:    { width: '100%', alignItems: 'center', justifyContent: 'center' },
  text:    { fontWeight: '700', letterSpacing: 0.2 },
  disabled:{ opacity: 0.5 },
  pressed: { opacity: 0.88, transform: [{ scale: 0.98 }] },
});
