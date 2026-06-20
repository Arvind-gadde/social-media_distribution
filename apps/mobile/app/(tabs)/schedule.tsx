import { StyleSheet, Text, View } from 'react-native';
import { COLORS, SPACE, TYPE } from '@/lib/theme';

export default function ScheduleScreen() {
  return (
    <View style={s.container}>
      <Text style={s.title}>Schedule</Text>
      <Text style={s.body}>
        Coming soon — view and manage scheduled posts here. For now use the web app.
      </Text>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, padding: SPACE.xl, backgroundColor: COLORS.dark.bg },
  title:     { ...TYPE.title, color: COLORS.dark.text, marginBottom: SPACE.sm },
  body:      { ...TYPE.body, color: COLORS.dark.textSecondary, lineHeight: 22 },
});
