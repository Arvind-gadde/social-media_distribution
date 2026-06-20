import { forwardRef } from 'react';
import { StyleSheet, Text, TextInput, TextInputProps, View } from 'react-native';
import { COLORS, RADIUS, SPACE, TYPE } from '@/lib/theme';

interface AppInputProps extends TextInputProps {
  label?:       string;
  labelRight?:  React.ReactNode;
  error?:       boolean;
  rightAction?: React.ReactNode;
}

export const AppInput = forwardRef<TextInput, AppInputProps>(
  ({ label, labelRight, error, rightAction, style, ...props }, ref) => (
    <View style={styles.wrapper}>
      {(label || labelRight) && (
        <View style={styles.labelRow}>
          {label     && <Text style={styles.label}>{label.toUpperCase()}</Text>}
          {labelRight}
        </View>
      )}
      <View style={styles.inputWrap}>
        <TextInput
          ref={ref}
          placeholderTextColor={COLORS.light.textTertiary}
          style={[styles.input, error && styles.inputError, rightAction ? styles.inputPadded : null, style]}
          {...props}
        />
        {rightAction && <View style={styles.right}>{rightAction}</View>}
      </View>
    </View>
  ),
);

AppInput.displayName = 'AppInput';

const styles = StyleSheet.create({
  wrapper:     { marginBottom: SPACE.lg },
  labelRow:    { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 7 },
  label:       { ...TYPE.label, color: COLORS.light.textTertiary },
  inputWrap:   { position: 'relative' },
  input: {
    backgroundColor: COLORS.light.surfaceAlt,
    color:           COLORS.light.text,
    paddingHorizontal: SPACE.lg,
    paddingVertical:   13,
    borderRadius:      RADIUS.lg,
    fontSize:          14,
    borderWidth:       1,
    borderColor:       COLORS.light.border,
  },
  inputError:  { borderColor: COLORS.errorBorder },
  inputPadded: { paddingRight: 48 },
  right:       { position: 'absolute', right: 14, top: 0, bottom: 0, justifyContent: 'center' },
});
