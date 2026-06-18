import { useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "@/lib/auth";

export default function LoginScreen() {
  const router = useRouter();
  const signIn = useAuth((s) => s.signIn);
  const biometricUnlock = useAuth((s) => s.biometricUnlock);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      await signIn(email, password);
      router.replace("/(tabs)/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function tryBiometric() {
    const ok = await biometricUnlock();
    if (ok) router.replace("/(tabs)/dashboard");
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>ContentFlow</Text>
      <Text style={styles.subtitle}>From idea to viral.</Text>

      <TextInput
        style={styles.input}
        placeholder="Email"
        placeholderTextColor="#94A3B8"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        placeholderTextColor="#94A3B8"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Pressable style={styles.primaryBtn} onPress={submit} disabled={submitting}>
        {submitting ? <ActivityIndicator color="white" /> : <Text style={styles.primaryBtnText}>Sign In</Text>}
      </Pressable>
      <Pressable style={styles.linkBtn} onPress={tryBiometric}>
        <Text style={styles.linkText}>Unlock with biometrics</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, justifyContent: "center", backgroundColor: "#0F172A" },
  title: { color: "#F8FAFC", fontSize: 32, fontWeight: "700", marginBottom: 4 },
  subtitle: { color: "#94A3B8", fontSize: 14, marginBottom: 32 },
  input: {
    backgroundColor: "#1E293B",
    color: "#F8FAFC",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderRadius: 12,
    marginBottom: 12,
  },
  primaryBtn: { backgroundColor: "#6366F1", paddingVertical: 14, borderRadius: 12, alignItems: "center", marginTop: 12 },
  primaryBtnText: { color: "white", fontSize: 16, fontWeight: "600" },
  linkBtn: { alignItems: "center", paddingVertical: 16 },
  linkText: { color: "#A5B4FC" },
  error: { color: "#FCA5A5", marginTop: 4 },
});
