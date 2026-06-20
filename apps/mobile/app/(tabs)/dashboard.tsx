import { useQuery } from '@tanstack/react-query';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { apiFetch } from '@/lib/api';
import { AppCard } from '@/components/ui/AppCard';
import { COLORS, SPACE, TYPE } from '@/lib/theme';

type Overview = {
  posts_this_month:    number;
  posts_limit:         number;
  platforms_connected: number;
  platforms_limit:     number;
};

export default function DashboardScreen() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['billing-usage'],
    queryFn:  () => apiFetch<Overview>('/api/v1/billing/usage'),
  });

  if (isLoading) {
    return (
      <View style={s.center}>
        <ActivityIndicator color={COLORS.dark.indicator} size="large" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={s.center}>
        <Text style={s.errorText}>{(error as Error).message}</Text>
      </View>
    );
  }

  return (
    <ScrollView style={s.container} contentContainerStyle={s.content}>
      <Text style={s.title}>Dashboard</Text>
      <StatCard label="Posts this month"     value={`${data?.posts_this_month ?? 0} / ${data?.posts_limit ?? 0}`} />
      <StatCard label="Connected platforms"  value={`${data?.platforms_connected ?? 0} / ${data?.platforms_limit ?? 0}`} />
    </ScrollView>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <AppCard>
      <Text style={s.cardLabel}>{label}</Text>
      <Text style={s.cardValue}>{value}</Text>
    </AppCard>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.dark.bg },
  content:   { padding: SPACE.xl },
  center:    { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: COLORS.dark.bg },
  title:     { ...TYPE.title, color: COLORS.dark.text, marginBottom: SPACE.lg },
  cardLabel: { color: COLORS.dark.textSecondary, marginBottom: SPACE.sm, fontSize: 13 },
  cardValue: { color: COLORS.dark.text, fontSize: 20, fontWeight: '600' },
  errorText: { color: COLORS.errorLight, fontSize: 14, textAlign: 'center', paddingHorizontal: SPACE['2xl'] },
});
