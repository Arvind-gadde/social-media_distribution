import { Text, View, StyleSheet } from "react-native";

export default function ScheduleScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Schedule</Text>
      <Text style={styles.body}>
        Coming soon — view and manage scheduled posts here. For now use the web app.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: "#020617" },
  title: { color: "#F8FAFC", fontSize: 24, fontWeight: "700", marginBottom: 8 },
  body: { color: "#94A3B8", lineHeight: 20 },
});
