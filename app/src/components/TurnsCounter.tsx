import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, fontSizes, borderRadius } from '../theme';

interface TurnsCounterProps {
  count: number;
  label?: string;
}

export function TurnsCounter({ count, label = 'Hoje' }: TurnsCounterProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.countContainer}>
        <Text style={styles.count}>{count}</Text>
        <Text style={styles.unit}>turns</Text>
      </View>
      <Text style={styles.subtitle}>conversational turns</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    paddingVertical: spacing.lg,
  },
  label: {
    fontSize: fontSizes.lg,
    fontWeight: '500',
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  countContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: spacing.sm,
  },
  count: {
    fontSize: fontSizes.hero,
    fontWeight: '700',
    color: colors.primary,
  },
  unit: {
    fontSize: fontSizes.xl,
    fontWeight: '500',
    color: colors.primaryLight,
  },
  subtitle: {
    fontSize: fontSizes.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
});
