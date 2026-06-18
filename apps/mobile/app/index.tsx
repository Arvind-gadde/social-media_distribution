import { Redirect } from "expo-router";
import { useAuth } from "@/lib/auth";

export default function Index() {
  const session = useAuth((s) => s.session);
  return session ? <Redirect href="/(tabs)/dashboard" /> : <Redirect href="/(auth)/login" />;
}
