import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, fontSizes } from '../theme';
import { BLEConnectionStatus } from '../types';

interface StatusIndicatorProps {
  status: BLEConnectionStatus;
  deviceName?: string | null;
}

const STATUS_CONFIG: Record<
  BLEConnectionStatus,
  { icon: string; color: string; label: string }
> = {
  disconnected: {
    icon: 'bluetooth-outline',
    color: colors.textMuted,
    label: 'Desconectado',
  },
  scanning: {
    icon: 'bluetooth-outline',
    color: colors.warning,
    label: 'Procurando...',
  },
  connecting: {
    icon: 'bluetooth',
    color: colors.warning,
    label: 'Conectando...',
  },
  connected: {
    icon: 'bluetooth',
    color: colors.success,
    label: 'Conectado',
  },
  error: {
    icon: 'alert-circle-outline',
    color: colors.error,
    label: 'Erro',
  },
};

export function StatusIndicator({ status, deviceName }: StatusIndicatorProps) {
  const config = STATUS_CONFIG[status];

  return (
    <View style={styles.container}>
      <View style={[styles.dot, { backgroundColor: config.color }]}>
        <Ionicons
          name={config.icon as any}
          size={16}
          color={colors.textOnPrimary}
        />
      </View>
      <View style={styles.textContainer}>
        <Text style={styles.status}>{config.label}</Text>
        {status === 'connected' && deviceName && (
          <Text style={styles.deviceName}>{deviceName}</Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  dot: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  textContainer: {
    flex: 1,
  },
  status: {
    fontSize: fontSizes.md,
    fontWeight: '500',
    color: colors.textPrimary,
  },
  deviceName: {
    fontSize: fontSizes.sm,
    color: colors.textSecondary,
  },
});
