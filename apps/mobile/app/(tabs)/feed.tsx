import { useQuery } from '@tanstack/react-query';
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native';
import { apiFetch } from '@/lib/api';
import { AppCard } from '@/components/ui/AppCard';
import { COLORS, SPACE, TYPE } from '@/lib/theme';

type ContentItem = { id: string; title: string; status: string; created_at: string };
type PaginatedContent = { items: ContentItem[] };

export default function FeedScreen() {
  // The legacy /api/v1/posts router is removed on the backend (superseded by
  // content-projects); hitting it 404'd and the feed silently showed empty.
  const { data, isLoading, error } = useQuery({
    queryKey: ['content-feed'],
    queryFn:  () => apiFetch<PaginatedContent>('/api/v1/content-projects?page_size=50'),
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
    <FlatList
      style={s.container}
      contentContainerStyle={s.content}
      data={data?.items ?? []}
      keyExtractor={(item) => item.id}
      ListEmptyComponent={<Text style={s.empty}>No posts yet.</Text>}
      renderItem={({ item }) => (
        <AppCard>
          <Text style={s.title}>{item.title}</Text>
          <Text style={s.meta}>{item.status} · {new Date(item.created_at).toLocaleString()}</Text>
        </AppCard>
      )}
    />
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.dark.bg },
  content:   { padding: SPACE.lg },
  center:    { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: COLORS.dark.bg },
  title:     { color: COLORS.dark.text, fontSize: 16, fontWeight: '600' },
  meta:      { color: COLORS.dark.textSecondary, fontSize: 12, marginTop: SPACE.xs },
  empty:     { color: COLORS.dark.textSecondary, textAlign: 'center', marginTop: SPACE['3xl'] },
  errorText: { color: COLORS.errorLight, fontSize: 14, textAlign: 'center', paddingHorizontal: SPACE['2xl'] },
});
