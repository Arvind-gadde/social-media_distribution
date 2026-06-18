import { useQuery } from "@tanstack/react-query";
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";
import { apiFetch } from "@/lib/api";

type Post = { id: string; title: string; status: string; created_at: string };

export default function FeedScreen() {
  const { data, isLoading } = useQuery({
    queryKey: ["posts-feed"],
    queryFn: () => apiFetch<Post[]>("/api/v1/posts?limit=50"),
  });

  if (isLoading) {
    return (
      <View style={[styles.container, styles.center]}>
        <ActivityIndicator color="#A5B4FC" />
      </View>
    );
  }

  return (
    <FlatList
      style={styles.container}
      contentContainerStyle={{ padding: 16 }}
      data={data ?? []}
      keyExtractor={(item) => item.id}
      ListEmptyComponent={<Text style={styles.empty}>No posts yet.</Text>}
      renderItem={({ item }) => (
        <View style={styles.row}>
          <Text style={styles.title}>{item.title}</Text>
          <Text style={styles.meta}>{item.status} • {new Date(item.created_at).toLocaleString()}</Text>
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#020617" },
  center: { alignItems: "center", justifyContent: "center" },
  row: { padding: 14, backgroundColor: "#0F172A", borderRadius: 12, marginBottom: 10 },
  title: { color: "#F8FAFC", fontSize: 16, fontWeight: "600" },
  meta: { color: "#94A3B8", fontSize: 12, marginTop: 4 },
  empty: { color: "#94A3B8", textAlign: "center", marginTop: 32 },
});
