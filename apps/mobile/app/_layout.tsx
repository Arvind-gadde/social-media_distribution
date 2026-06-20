import { Stack } from "expo-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { StatusBar } from "expo-status-bar";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { LockScreen } from "@/components/LockScreen";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

export default function RootLayout() {
  const loadFromStorage = useAuth((s) => s.loadFromStorage);
  const locked = useAuth((s) => s.locked);
  const [bootstrapped, setBootstrapped] = useState(false);

  useEffect(() => {
    loadFromStorage().finally(() => setBootstrapped(true));
  }, [loadFromStorage]);

  if (!bootstrapped) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <StatusBar style="auto" />
        {locked ? (
          // A restored session is held behind the biometric lock — gate the
          // whole app until the user unlocks (or falls back to password).
          <LockScreen />
        ) : (
          <Stack screenOptions={{ headerShown: false }}>
            <Stack.Screen name="(auth)" />
            <Stack.Screen name="(tabs)" />
          </Stack>
        )}
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}
