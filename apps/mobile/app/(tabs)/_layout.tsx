import { Redirect, Tabs } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useAuth } from '@/lib/auth';
import { COLORS } from '@/lib/theme';

export default function TabsLayout() {
  // Guard the protected route group itself, not just the index route — deep
  // links, notifications, restored navigation state, or a logout while mounted
  // could otherwise land on a tab screen with no session.
  const session = useAuth((s) => s.session);
  const hydrated = useAuth((s) => s.hydrated);
  if (!hydrated) return null;
  if (!session) return <Redirect href="/(auth)/login" />;

  return (
    <>
    {/* App screens use the dark theme → light status-bar text for legibility. */}
    <StatusBar style="light" />
    <Tabs
      screenOptions={{
        headerStyle:           { backgroundColor: COLORS.dark.surface },
        headerTintColor:       COLORS.dark.text,
        tabBarStyle:           { backgroundColor: COLORS.dark.surface, borderTopColor: COLORS.dark.border },
        tabBarActiveTintColor: COLORS.dark.indicator,
        tabBarInactiveTintColor: COLORS.dark.textTertiary,
      }}
    >
      <Tabs.Screen name="dashboard" options={{ title: 'Dashboard' }} />
      <Tabs.Screen name="feed"      options={{ title: 'Feed'      }} />
      <Tabs.Screen name="schedule"  options={{ title: 'Schedule'  }} />
      <Tabs.Screen name="settings"  options={{ title: 'Settings'  }} />
    </Tabs>
    </>
  );
}
