import { useState } from 'react';
import { Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '@/lib/auth';
import { AppButton } from '@/components/ui/AppButton';
import { AppInput } from '@/components/ui/AppInput';
import { COLORS, RADIUS, SPACE, TYPE, SHADOW } from '@/lib/theme';

export default function LoginScreen() {
  const router            = useRouter();
  const signIn            = useAuth((s) => s.signIn);
  const [email, setEmail]           = useState('');
  const [password, setPassword]     = useState('');
  const [showPwd, setShowPwd]       = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]           = useState<string | null>(null);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaCode, setMfaCode]         = useState('');

  async function submit() {
    if (!email || !password) return;
    if (mfaRequired && !mfaCode) return;
    setSubmitting(true);
    setError(null);
    try {
      const { mfaRequired: need } = await signIn(email, password, mfaCode || undefined);
      if (need) {
        setMfaRequired(true);
        return;
      }
      router.replace('/(tabs)/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed. Please try again.');
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

        <Text style={s.heading}>Welcome back</Text>
        <Text style={s.subheading}>Sign in to your content studio</Text>

        {error ? (
          <View style={s.errorBox}>
            <Text style={s.errorText}>{error}</Text>
          </View>
        ) : null}

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
          labelRight={<Text style={s.forgotText}>Forgot?</Text>}
          value={password}
          onChangeText={setPassword}
          placeholder="Enter your password"
          secureTextEntry={!showPwd}
          autoComplete="current-password"
          rightAction={
            <Pressable onPress={() => setShowPwd(!showPwd)}>
              <Text style={s.eyeIcon}>{showPwd ? '🙈' : '👁'}</Text>
            </Pressable>
          }
        />

        {mfaRequired && (
          <AppInput
            label="Authentication code"
            value={mfaCode}
            onChangeText={setMfaCode}
            placeholder="6-digit code or backup code"
            keyboardType="number-pad"
            autoComplete="one-time-code"
          />
        )}

        <AppButton onPress={submit} loading={submitting} disabled={!email || !password || (mfaRequired && !mfaCode)}>
          {mfaRequired ? 'Verify code  →' : 'Sign in  →'}
        </AppButton>

        <View style={s.footer}>
          <Text style={s.footerText}>No account? </Text>
          <Pressable onPress={() => router.push('/(auth)/register' as never)}>
            <Text style={s.footerLink}>Create one free</Text>
          </Pressable>
        </View>

        <Text style={s.legal}>By signing in you agree to our Terms &amp; Privacy Policy</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe:        { flex: 1, backgroundColor: COLORS.light.bg },
  scroll:      { flexGrow: 1, paddingHorizontal: SPACE['2xl'], paddingTop: SPACE['3xl'], paddingBottom: SPACE['4xl'], justifyContent: 'center' },

  logoRow:  { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: SPACE['4xl'] },
  logoBox:  { width: 36, height: 36, borderRadius: RADIUS.md, backgroundColor: COLORS.logoIconBg, alignItems: 'center', justifyContent: 'center' },
  logoIcon: { fontSize: 17 },
  logoText: { ...TYPE.brand, color: COLORS.light.text },

  heading:    { ...TYPE.heading, color: COLORS.light.text, marginBottom: SPACE.xs },
  subheading: { ...TYPE.body, color: COLORS.light.textSecondary, marginBottom: SPACE['2xl'] },

  errorBox:  { backgroundColor: COLORS.errorLight, borderWidth: 1, borderColor: COLORS.errorBorder, borderRadius: RADIUS.md, padding: SPACE.md, marginBottom: SPACE.lg },
  errorText: { color: COLORS.errorText, fontSize: 13, lineHeight: 18 },

  forgotText: { fontSize: 12, fontWeight: '600', color: COLORS.primary },
  eyeIcon:    { fontSize: 16 },

  divider:     { flexDirection: 'row', alignItems: 'center', marginVertical: SPACE.xl, gap: 10 },
  dividerLine: { flex: 1, height: 1, backgroundColor: COLORS.light.border },
  dividerText: { ...TYPE.label, color: COLORS.light.textTertiary },

  footer:     { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginTop: SPACE['2xl'], marginBottom: SPACE.md },
  footerText: { fontSize: 13, color: COLORS.light.textSecondary },
  footerLink: { fontSize: 13, fontWeight: '700', color: COLORS.primary },
  legal:      { textAlign: 'center', fontSize: 10, color: COLORS.light.textTertiary, lineHeight: 16 },
});
