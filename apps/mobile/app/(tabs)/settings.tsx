import { Pressable, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "@/lib/auth";

export default function SettingsScreen() {
  const router = useRouter();
  const signOut = useAuth((s) => s.signOut);
  const session = useAuth((s) => s.session);

  async function handleSignOut() {
    await signOut();
    router.replace("/(auth)/login");
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Settings</Text>
      <View style={styles.card}>
        <Text style={styles.label}>Signed in as</Text>
        <Text style={styles.value}>{session?.email ?? "—"}</Text>
      </View>
      <Pressable style={styles.dangerBtn} onPress={handleSignOut}>
        <Text style={styles.dangerText}>Sign out</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: "#020617" },
  title: { color: "#F8FAFC", fontSize: 24, fontWeight: "700", marginBottom: 16 },
  card: { backgroundColor: "#0F172A", padding: 16, borderRadius: 12, marginBottom: 24 },
  label: { color: "#94A3B8", marginBottom: 4 },
  value: { color: "#F8FAFC", fontSize: 16, fontWeight: "600" },
  dangerBtn: { backgroundColor: "#1E293B", borderRadius: 12, paddingVertical: 14, alignItems: "center" },
  dangerText: { color: "#FCA5A5", fontWeight: "600" },
});
