import { useQuery } from "@tanstack/react-query";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { apiFetch } from "@/lib/api";

type Overview = {
  posts_this_month: number;
  posts_limit: number;
  platforms_connected: number;
  platforms_limit: number;
};

export default function DashboardScreen() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["billing-usage"],
    queryFn: () => apiFetch<Overview>("/api/v1/billing/usage"),
  });

  if (isLoading) return <Loading />;
  if (error) return <ErrorBox message={(error as Error).message} />;

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 20 }}>
      <Text style={styles.h1}>Dashboard</Text>
      <Card label="Posts this month" value={`${data?.posts_this_month ?? 0} / ${data?.posts_limit ?? 0}`} />
      <Card label="Connected platforms" value={`${data?.platforms_connected ?? 0} / ${data?.platforms_limit ?? 0}`} />
    </ScrollView>
  );
}

function Card({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardLabel}>{label}</Text>
      <Text style={styles.cardValue}>{value}</Text>
    </View>
  );
}

function Loading() {
  return (
    <View style={[styles.container, styles.center]}>
      <ActivityIndicator color="#A5B4FC" />
    </View>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <View style={[styles.container, styles.center]}>
      <Text style={{ color: "#FCA5A5" }}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#020617" },
  center: { alignItems: "center", justifyContent: "center" },
  h1: { color: "#F8FAFC", fontSize: 24, fontWeight: "700", marginBottom: 16 },
  card: { backgroundColor: "#0F172A", padding: 18, borderRadius: 14, marginBottom: 12 },
  cardLabel: { color: "#94A3B8", marginBottom: 6 },
  cardValue: { color: "#F8FAFC", fontSize: 20, fontWeight: "600" },
});
