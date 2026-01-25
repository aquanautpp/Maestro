/**
 * Home Screen
 *
 * - Device connection status
 * - Start/Stop session button
 * - Today's turns summary
 */

import React, { useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, fontSizes, borderRadius, shadows } from '../theme';
import { Button, Card, StatusIndicator, TurnsCounter } from '../components';
import { useBLE, useSession } from '../hooks';

export function HomeScreen() {
  const {
    status: bleStatus,
    device,
    discoveredDevices,
    error: bleError,
    isScanning,
    scan,
    connect,
    disconnect,
    onEvent,
  } = useBLE();

  const {
    isActive: isSessionActive,
    todayTurns,
    currentSession,
    startSession,
    stopSession,
    addEvent,
  } = useSession();

  // Connect BLE events to session
  useEffect(() => {
    onEvent((event) => {
      if (isSessionActive) {
        addEvent(event);
      }
    });
  }, [onEvent, isSessionActive, addEvent]);

  // Handle device connection
  const handleConnect = useCallback(async () => {
    if (bleStatus === 'connected') {
      await disconnect();
    } else if (discoveredDevices.length > 0) {
      // Auto-connect to first device
      await connect(discoveredDevices[0].id);
    } else {
      await scan();
    }
  }, [bleStatus, discoveredDevices, connect, disconnect, scan]);

  // Handle session toggle
  const handleSessionToggle = useCallback(async () => {
    if (isSessionActive) {
      const summary = await stopSession();
      if (summary) {
        const turns = summary.totalServes + summary.totalReturns;
        // Summary is shown via notification
      }
    } else {
      if (bleStatus !== 'connected') {
        Alert.alert(
          'Dispositivo não conectado',
          'Conecte o dispositivo primeiro para iniciar uma sessão.',
          [{ text: 'OK' }]
        );
        return;
      }
      await startSession();
    }
  }, [isSessionActive, bleStatus, startSession, stopSession]);

  // Auto-connect when device is found
  useEffect(() => {
    if (discoveredDevices.length > 0 && bleStatus === 'disconnected') {
      connect(discoveredDevices[0].id);
    }
  }, [discoveredDevices, bleStatus, connect]);

  const sessionDuration = currentSession
    ? Math.floor((Date.now() - currentSession.startedAt.getTime()) / 60000)
    : 0;

  const sessionTurns = currentSession?.events.filter(
    (e) => e.type === 'serve' || e.type === 'return'
  ).length || 0;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.greeting}>Olá! 👋</Text>
          <Text style={styles.subtitle}>Vamos conversar?</Text>
        </View>

        {/* Device Status Card */}
        <Card style={styles.statusCard}>
          <StatusIndicator status={bleStatus} deviceName={device?.name} />

          {bleError && (
            <Text style={styles.errorText}>{bleError}</Text>
          )}

          {bleStatus === 'disconnected' && (
            <Button
              title={isScanning ? 'Procurando...' : 'Conectar dispositivo'}
              onPress={handleConnect}
              variant="outline"
              size="small"
              loading={isScanning}
              style={styles.connectButton}
            />
          )}

          {bleStatus === 'connected' && !isSessionActive && (
            <Button
              title="Desconectar"
              onPress={disconnect}
              variant="outline"
              size="small"
              style={styles.connectButton}
            />
          )}
        </Card>

        {/* Active Session Card */}
        {isSessionActive && (
          <Card style={styles.activeSessionCard}>
            <View style={styles.activeSessionHeader}>
              <View style={styles.recordingDot} />
              <Text style={styles.activeSessionText}>Sessão em andamento</Text>
            </View>
            <View style={styles.sessionStats}>
              <View style={styles.sessionStat}>
                <Text style={styles.sessionStatValue}>{sessionDuration}</Text>
                <Text style={styles.sessionStatLabel}>min</Text>
              </View>
              <View style={styles.sessionStatDivider} />
              <View style={styles.sessionStat}>
                <Text style={styles.sessionStatValue}>{sessionTurns}</Text>
                <Text style={styles.sessionStatLabel}>turns</Text>
              </View>
            </View>
          </Card>
        )}

        {/* Today's Summary */}
        <Card elevated style={styles.summaryCard}>
          <TurnsCounter count={todayTurns} />
        </Card>

        {/* Main Action Button */}
        <Button
          title={isSessionActive ? 'Parar sessão' : 'Iniciar sessão'}
          onPress={handleSessionToggle}
          variant={isSessionActive ? 'secondary' : 'primary'}
          size="large"
          disabled={!isSessionActive && bleStatus !== 'connected'}
          style={styles.mainButton}
        />

        {/* Encouragement message */}
        {!isSessionActive && (
          <Text style={styles.encouragement}>
            {bleStatus === 'connected'
              ? 'Pronto para começar! 🎉'
              : 'Conecte o dispositivo para iniciar'}
          </Text>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    padding: spacing.lg,
    paddingBottom: spacing.xxl,
  },

  // Header
  header: {
    marginBottom: spacing.lg,
  },
  greeting: {
    fontSize: fontSizes.xxl,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  subtitle: {
    fontSize: fontSizes.lg,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },

  // Status Card
  statusCard: {
    marginBottom: spacing.md,
  },
  connectButton: {
    marginTop: spacing.md,
    alignSelf: 'flex-start',
  },
  errorText: {
    color: colors.error,
    fontSize: fontSizes.sm,
    marginTop: spacing.sm,
  },

  // Active Session Card
  activeSessionCard: {
    backgroundColor: colors.primaryLight,
    marginBottom: spacing.md,
  },
  activeSessionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  recordingDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: colors.error,
  },
  activeSessionText: {
    fontSize: fontSizes.md,
    fontWeight: '600',
    color: colors.textOnPrimary,
  },
  sessionStats: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: spacing.lg,
  },
  sessionStat: {
    alignItems: 'center',
  },
  sessionStatValue: {
    fontSize: fontSizes.xxl,
    fontWeight: '700',
    color: colors.textOnPrimary,
  },
  sessionStatLabel: {
    fontSize: fontSizes.sm,
    color: colors.textOnPrimary,
    opacity: 0.8,
  },
  sessionStatDivider: {
    width: 1,
    height: 40,
    backgroundColor: colors.textOnPrimary,
    opacity: 0.3,
  },

  // Summary Card
  summaryCard: {
    marginBottom: spacing.xl,
  },

  // Main Button
  mainButton: {
    marginBottom: spacing.md,
  },

  // Encouragement
  encouragement: {
    textAlign: 'center',
    fontSize: fontSizes.md,
    color: colors.textSecondary,
  },
});
