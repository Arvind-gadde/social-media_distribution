import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useAuth } from '@/lib/auth';
import { AppButton } from '@/components/ui/AppButton';
import { COLORS, SPACE, TYPE } from '@/lib/theme';

/**
 * Biometric lock gate. Rendered (instead of the app) when a restored session
 * is held behind the opt-in biometric lock. Unlock reveals the app; "Use
 * password instead" signs out and returns to the login screen.
 */
export function LockScreen() {
  const unlock = useAuth((s) => s.unlock);
  const signOut = useAuth((s) => s.signOut);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function attempt() {
    setBusy(true);
    setError(null);
    const ok = await unlock();
    if (!ok) setError('Authentication failed. Try again, or use your password.');
    setBusy(false);
  }

  // Prompt automatically on mount so unlocking is one tap (or zero).
  useEffect(() => {
    attempt();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <View style={s.container}>
      <Text style={s.icon}>🔒</Text>
      <Text style={s.title}>ContentFlow is locked</Text>
      <Text style={s.subtitle}>Unlock with biometrics to continue.</Text>
      {error ? <Text style={s.error}>{error}</Text> : null}
      <View style={s.actions}>
        <AppButton onPress={attempt} loading={busy}>Unlock</AppButton>
        <AppButton variant="ghost" onPress={signOut} style={{ marginTop: SPACE.md }}>
          Use password instead
        </AppButton>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: SPACE['2xl'], backgroundColor: COLORS.dark.bg },
  icon:      { fontSize: 44, marginBottom: SPACE.lg },
  title:     { ...TYPE.title, color: COLORS.dark.text, marginBottom: SPACE.xs, textAlign: 'center' },
  subtitle:  { ...TYPE.body, color: COLORS.dark.textSecondary, textAlign: 'center' },
  error:     { color: COLORS.errorLight, fontSize: 13, textAlign: 'center', marginTop: SPACE.md },
  actions:   { width: '100%', marginTop: SPACE['2xl'] },
});
