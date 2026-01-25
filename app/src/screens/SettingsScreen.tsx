/**
 * Settings Screen
 *
 * - Data sharing consent options
 * - Device ID (for debug)
 * - Sync status
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Switch,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, fontSizes, borderRadius } from '../theme';
import { Card } from '../components';
import { useSync } from '../hooks';
import {
  getSettings,
  saveSettings,
  getOrCreateDeviceId,
} from '../services/storage';
import { DataSharingMode, AppSettings } from '../types';

export function SettingsScreen() {
  const { status: syncStatus, sync } = useSync();
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [deviceId, setDeviceId] = useState<string>('');

  // Load settings
  useEffect(() => {
    const load = async () => {
      const loadedSettings = await getSettings();
      setSettings(loadedSettings);

      const id = await getOrCreateDeviceId();
      setDeviceId(id);
    };
    load();
  }, []);

  // Update data sharing mode
  const handleDataSharingChange = async (mode: DataSharingMode) => {
    if (!settings) return;

    const newSettings = { ...settings, dataSharingMode: mode };
    setSettings(newSettings);
    await saveSettings({ dataSharingMode: mode });
  };

  // Manual sync
  const handleSync = async () => {
    await sync();
    Alert.alert('Sincronização', 'Dados sincronizados com sucesso!');
  };

  if (!settings) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loading}>
          <Text>Carregando...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Configurações</Text>
        </View>

        {/* Data Sharing Section */}
        <Text style={styles.sectionTitle}>Compartilhamento de dados</Text>
        <Card style={styles.optionsCard}>
          <TouchableOpacity
            style={styles.option}
            onPress={() => handleDataSharingChange('coach_only')}
          >
            <View style={styles.optionContent}>
              <Ionicons
                name={
                  settings.dataSharingMode === 'coach_only'
                    ? 'radio-button-on'
                    : 'radio-button-off'
                }
                size={24}
                color={
                  settings.dataSharingMode === 'coach_only'
                    ? colors.primary
                    : colors.textMuted
                }
              />
              <View style={styles.optionText}>
                <Text style={styles.optionTitle}>Modo Coach</Text>
                <Text style={styles.optionDescription}>
                  Seus dados ficam apenas com você e a equipe do Coach
                </Text>
              </View>
            </View>
          </TouchableOpacity>

          <View style={styles.optionDivider} />

          <TouchableOpacity
            style={styles.option}
            onPress={() => handleDataSharingChange('coach_and_school')}
          >
            <View style={styles.optionContent}>
              <Ionicons
                name={
                  settings.dataSharingMode === 'coach_and_school'
                    ? 'radio-button-on'
                    : 'radio-button-off'
                }
                size={24}
                color={
                  settings.dataSharingMode === 'coach_and_school'
                    ? colors.primary
                    : colors.textMuted
                }
              />
              <View style={styles.optionText}>
                <Text style={styles.optionTitle}>Modo Coach + Escola</Text>
                <Text style={styles.optionDescription}>
                  Compartilha resumos anônimos com a escola do seu filho
                </Text>
              </View>
            </View>
          </TouchableOpacity>
        </Card>

        {/* Privacy Info */}
        <Card style={styles.infoCard}>
          <Ionicons name="shield-checkmark" size={24} color={colors.primary} />
          <Text style={styles.infoText}>
            Seus áudios nunca são gravados ou enviados. Apenas estatísticas
            anônimas são armazenadas.
          </Text>
        </Card>

        {/* Sync Section */}
        <Text style={styles.sectionTitle}>Sincronização</Text>
        <Card style={styles.syncCard}>
          <View style={styles.syncRow}>
            <Text style={styles.syncLabel}>Eventos pendentes</Text>
            <Text style={styles.syncValue}>{syncStatus.pendingEvents}</Text>
          </View>

          <View style={styles.syncRow}>
            <Text style={styles.syncLabel}>Última sincronização</Text>
            <Text style={styles.syncValue}>
              {syncStatus.lastSyncAt
                ? syncStatus.lastSyncAt.toLocaleTimeString('pt-BR')
                : 'Nunca'}
            </Text>
          </View>

          <TouchableOpacity
            style={styles.syncButton}
            onPress={handleSync}
            disabled={syncStatus.isSyncing}
          >
            <Ionicons
              name="sync"
              size={20}
              color={colors.primary}
              style={syncStatus.isSyncing ? styles.spinning : undefined}
            />
            <Text style={styles.syncButtonText}>
              {syncStatus.isSyncing ? 'Sincronizando...' : 'Sincronizar agora'}
            </Text>
          </TouchableOpacity>
        </Card>

        {/* Device Info */}
        <Text style={styles.sectionTitle}>Informações do dispositivo</Text>
        <Card style={styles.deviceCard}>
          <View style={styles.deviceRow}>
            <Text style={styles.deviceLabel}>Device ID</Text>
            <Text style={styles.deviceValue} selectable>
              {deviceId}
            </Text>
          </View>
        </Card>

        {/* Version */}
        <Text style={styles.version}>Early Childhood Coach v0.1.0</Text>
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
  loading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },

  // Header
  header: {
    marginBottom: spacing.lg,
  },
  title: {
    fontSize: fontSizes.xxl,
    fontWeight: '700',
    color: colors.textPrimary,
  },

  // Section
  sectionTitle: {
    fontSize: fontSizes.sm,
    fontWeight: '600',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: spacing.sm,
    marginTop: spacing.md,
  },

  // Options Card
  optionsCard: {
    padding: 0,
    overflow: 'hidden',
  },
  option: {
    padding: spacing.md,
  },
  optionContent: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
  },
  optionText: {
    flex: 1,
  },
  optionTitle: {
    fontSize: fontSizes.md,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  optionDescription: {
    fontSize: fontSizes.sm,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  optionDivider: {
    height: 1,
    backgroundColor: colors.divider,
    marginHorizontal: spacing.md,
  },

  // Info Card
  infoCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    backgroundColor: colors.primaryLight + '20',
    marginTop: spacing.md,
  },
  infoText: {
    flex: 1,
    fontSize: fontSizes.sm,
    color: colors.textSecondary,
    lineHeight: 20,
  },

  // Sync Card
  syncCard: {
    gap: spacing.md,
  },
  syncRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  syncLabel: {
    fontSize: fontSizes.md,
    color: colors.textSecondary,
  },
  syncValue: {
    fontSize: fontSizes.md,
    fontWeight: '500',
    color: colors.textPrimary,
  },
  syncButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
    marginTop: spacing.sm,
  },
  syncButtonText: {
    fontSize: fontSizes.md,
    color: colors.primary,
    fontWeight: '500',
  },
  spinning: {
    // Animation would go here
  },

  // Device Card
  deviceCard: {
    gap: spacing.sm,
  },
  deviceRow: {
    gap: spacing.xs,
  },
  deviceLabel: {
    fontSize: fontSizes.sm,
    color: colors.textMuted,
  },
  deviceValue: {
    fontSize: fontSizes.sm,
    fontFamily: 'monospace',
    color: colors.textSecondary,
  },

  // Version
  version: {
    textAlign: 'center',
    fontSize: fontSizes.sm,
    color: colors.textMuted,
    marginTop: spacing.xl,
  },
});
