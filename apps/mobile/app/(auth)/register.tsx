import { useState } from 'react';
import { Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '@/lib/auth';
import { AppButton } from '@/components/ui/AppButton';
import { AppInput } from '@/components/ui/AppInput';
import { COLORS, RADIUS, SPACE, TYPE } from '@/lib/theme';

const PWD_RULES = [
  { key: 'length',  label: '8+ characters',    test: (p: string) => p.length >= 8 },
  { key: 'upper',   label: 'Uppercase letter',  test: (p: string) => /[A-Z]/.test(p) },
  { key: 'lower',   label: 'Lowercase letter',  test: (p: string) => /[a-z]/.test(p) },
  { key: 'number',  label: 'Number',            test: (p: string) => /[0-9]/.test(p) },
  { key: 'special', label: 'Special character', test: (p: string) => /[^A-Za-z0-9]/.test(p) },
];

const STRENGTH_COLOR = ['#F87171', '#F87171', '#FBBF24', '#FBBF24', '#60A5FA', '#34D399'];
const STRENGTH_LABEL = ['', 'Weak', 'Weak', 'Fair', 'Good', 'Strong'];

export default function RegisterScreen() {
  const router = useRouter();
  const signUp = useAuth((s) => s.signUp);
  const [name, setName]               = useState('');
  const [email, setEmail]             = useState('');
  const [password, setPassword]       = useState('');
  const [confirm, setConfirm]         = useState('');
  const [showPwd, setShowPwd]         = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [submitting, setSubmitting]   = useState(false);
  const [error, setError]             = useState<string | null>(null);

  const rules    = PWD_RULES.map((r) => ({ ...r, met: r.test(password) }));
  const strength = rules.filter((r) => r.met).length;
  const allMet   = strength === PWD_RULES.length;
  const pwdMatch = password === confirm && confirm.length > 0;
  const canSubmit = name.trim().length >= 2 && email && allMet && pwdMatch && !submitting;

  async function submit() {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await signUp({ email, password, name: name.trim() });
      router.replace('/(tabs)/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <SafeAreaView style={s.safe}>
      <ScrollView
        contentContainerStyle={s.scroll}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* Brand */}
        <View style={s.logoRow}>
          <View style={s.logoBox}>
            <Text style={s.logoIcon}>⚡</Text>
          </View>
          <Text style={s.logoText}>ContentFlow</Text>
        </View>

        <Text style={s.heading}>Create account</Text>
        <Text style={s.subheading}>Join creators on ContentFlow</Text>

        {error ? (
          <View style={s.errorBox}>
            <Text style={s.errorText}>{error}</Text>
          </View>
        ) : null}

        <AppInput label="Full name" value={name} onChangeText={setName} placeholder="Alex Johnson" autoComplete="name" />

        <AppInput
          label="Email"
          value={email}
          onChangeText={setEmail}
          placeholder="you@example.com"
          autoCapitalize="none"
          keyboardType="email-address"
          autoComplete="email"
        />

        <AppInput
          label="Password"
          value={password}
          onChangeText={setPassword}
          placeholder="Create a strong password"
          secureTextEntry={!showPwd}
          autoComplete="new-password"
          rightAction={
            <Pressable onPress={() => setShowPwd(!showPwd)}>
              <Text style={s.eyeIcon}>{showPwd ? '🙈' : '👁'}</Text>
            </Pressable>
          }
        />

        {/* Strength meter */}
        {password.length > 0 && (
          <View style={s.strengthSection}>
            <View style={s.strengthRow}>
              <View style={s.strengthTrack}>
                <View style={[s.strengthFill, { width: `${(strength / 5) * 100}%` as any, backgroundColor: STRENGTH_COLOR[strength] }]} />
              </View>
              <Text style={[s.strengthLabel, { color: STRENGTH_COLOR[strength] }]}>{STRENGTH_LABEL[strength]}</Text>
            </View>
            <View style={s.rulesBox}>
              {rules.map(({ key, label, met }) => (
                <View key={key} style={s.ruleRow}>
                  <Text style={met ? s.ruleOk : s.ruleNo}>{met ? '✓' : '×'}</Text>
                  <Text style={met ? s.ruleLabelOk : s.ruleLabelNo}>{label}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        <AppInput
          label="Confirm password"
          value={confirm}
          onChangeText={setConfirm}
          placeholder="Repeat your password"
          secureTextEntry={!showConfirm}
          autoComplete="new-password"
          error={!!confirm && !pwdMatch}
          rightAction={
            <Pressable onPress={() => setShowConfirm(!showConfirm)}>
              <Text style={s.eyeIcon}>{showConfirm ? '🙈' : '👁'}</Text>
            </Pressable>
          }
        />
        {confirm.length > 0 && !pwdMatch && <Text style={s.matchError}>× Passwords do not match</Text>}
        {pwdMatch                           && <Text style={s.matchOk}>✓ Passwords match</Text>}

        <AppButton onPress={submit} loading={submitting} disabled={!canSubmit} style={{ marginTop: SPACE.sm }}>
          Create account  →
        </AppButton>

        <View style={s.footer}>
          <Text style={s.footerText}>Already have an account? </Text>
          <Pressable onPress={() => router.back()}>
            <Text style={s.footerLink}>Sign in</Text>
          </Pressable>
        </View>

        <Text style={s.legal}>By creating an account you agree to our Terms &amp; Privacy Policy</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe:   { flex: 1, backgroundColor: COLORS.light.bg },
  scroll: { flexGrow: 1, paddingHorizontal: SPACE['2xl'], paddingTop: SPACE['3xl'], paddingBottom: SPACE['4xl'] },

  logoRow:  { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: SPACE['3xl'] + SPACE.sm },
  logoBox:  { width: 36, height: 36, borderRadius: RADIUS.md, backgroundColor: COLORS.logoIconBg, alignItems: 'center', justifyContent: 'center' },
  logoIcon: { fontSize: 17 },
  logoText: { ...TYPE.brand, color: COLORS.light.text },

  heading:    { ...TYPE.heading, color: COLORS.light.text, marginBottom: SPACE.xs },
  subheading: { ...TYPE.body, color: COLORS.light.textSecondary, marginBottom: SPACE['2xl'] },

  errorBox:  { backgroundColor: COLORS.errorLight, borderWidth: 1, borderColor: COLORS.errorBorder, borderRadius: RADIUS.md, padding: SPACE.md, marginBottom: SPACE.lg },
  errorText: { color: COLORS.errorText, fontSize: 13, lineHeight: 18 },

  eyeIcon: { fontSize: 16 },

  strengthSection: { marginTop: -SPACE.md, marginBottom: SPACE.lg },
  strengthRow:     { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: SPACE.sm },
  strengthTrack:   { flex: 1, height: 4, borderRadius: 2, backgroundColor: COLORS.light.border, overflow: 'hidden' },
  strengthFill:    { height: '100%', borderRadius: 2 },
  strengthLabel:   { fontSize: 10, fontWeight: '700', width: 36, textAlign: 'right' },

  rulesBox: { backgroundColor: COLORS.light.surfaceAlt, borderRadius: RADIUS.md, padding: SPACE.md, gap: 4 },
  ruleRow:  { flexDirection: 'row', alignItems: 'center', gap: 6 },
  ruleOk:       { color: COLORS.success, fontSize: 12, fontWeight: '700', width: 12 },
  ruleNo:       { color: COLORS.light.textTertiary, fontSize: 12, fontWeight: '700', width: 12 },
  ruleLabelOk:  { color: COLORS.successText, fontSize: 11 },
  ruleLabelNo:  { color: COLORS.light.textTertiary, fontSize: 11 },

  matchError: { color: COLORS.error, fontSize: 11, marginBottom: SPACE.md, marginTop: 2 },
  matchOk:    { color: COLORS.success, fontSize: 11, marginBottom: SPACE.md, marginTop: 2 },

  footer:     { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginTop: SPACE['2xl'], marginBottom: SPACE.md },
  footerText: { fontSize: 13, color: COLORS.light.textSecondary },
  footerLink: { fontSize: 13, fontWeight: '700', color: COLORS.primary },
  legal:      { textAlign: 'center', fontSize: 10, color: COLORS.light.textTertiary, lineHeight: 16 },
});
