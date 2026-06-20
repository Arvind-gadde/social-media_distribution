import { useEffect, useState } from 'react';
import { StyleSheet, Switch, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '@/lib/auth';
import { AppButton } from '@/components/ui/AppButton';
import { AppCard } from '@/components/ui/AppCard';
import { COLORS, SPACE, TYPE } from '@/lib/theme';

export default function SettingsScreen() {
  const router            = useRouter();
  const signOut           = useAuth((s) => s.signOut);
  const session           = useAuth((s) => s.session);
  const biometricEnabled  = useAuth((s) => s.biometricEnabled);
  const enableBiometric   = useAuth((s) => s.enableBiometric);
  const disableBiometric  = useAuth((s) => s.disableBiometric);
  const biometricAvailable = useAuth((s) => s.biometricAvailable);

  const [available, setAvailable] = useState(false);
  const [working, setWorking]     = useState(false);

  useEffect(() => {
    biometricAvailable().then(setAvailable);
  }, [biometricAvailable]);

  async function toggleBiometric(next: boolean) {
    setWorking(true);
    try {
      if (next) await enableBiometric();
      else await disableBiometric();
    } finally {
      setWorking(false);
    }
  }

  async function handleSignOut() {
    await signOut();
    router.replace('/(auth)/login');
  }

  return (
    <View style={s.container}>
      <Text style={s.title}>Settings</Text>

      <AppCard>
        <Text style={s.cardLabel}>Signed in as</Text>
        <Text style={s.cardValue}>{session?.email ?? '—'}</Text>
      </AppCard>

      {available && (
        <AppCard>
          <View style={s.row}>
            <View style={s.rowText}>
              <Text style={s.cardValue}>Biometric unlock</Text>
              <Text style={s.cardHint}>Require Face ID / fingerprint to open the app</Text>
            </View>
            <Switch
              value={biometricEnabled}
              onValueChange={toggleBiometric}
              disabled={working}
              trackColor={{ true: COLORS.primary, false: COLORS.dark.border }}
              thumbColor={COLORS.dark.text}
            />
          </View>
        </AppCard>
      )}

      <AppButton variant="danger" onPress={handleSignOut} style={{ marginTop: SPACE.md }}>
        Sign out
      </AppButton>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, padding: SPACE.xl, backgroundColor: COLORS.dark.bg },
  title:     { ...TYPE.title, color: COLORS.dark.text, marginBottom: SPACE.lg },
  cardLabel: { color: COLORS.dark.textSecondary, marginBottom: SPACE.xs, fontSize: 13 },
  cardValue: { color: COLORS.dark.text, fontSize: 16, fontWeight: '600' },
  cardHint:  { color: COLORS.dark.textSecondary, fontSize: 12, marginTop: 2 },
  row:       { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: SPACE.lg },
  rowText:   { flex: 1 },
});
