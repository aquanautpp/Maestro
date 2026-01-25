/**
 * Early Childhood Coach
 *
 * A wearable companion app that helps parents engage in more
 * conversational turns with their children.
 */

import React, { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AppNavigator } from './src/navigation/AppNavigator';
import { requestNotificationPermissions } from './src/services/notifications';
import { getOrCreateDeviceId, saveSettings } from './src/services/storage';
import { colors } from './src/theme';

export default function App() {
  // Initialize app on mount
  useEffect(() => {
    const initialize = async () => {
      // Ensure device ID exists
      const deviceId = await getOrCreateDeviceId();
      await saveSettings({ deviceId });

      // Request notification permissions
      await requestNotificationPermissions();
    };

    initialize();
  }, []);

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" backgroundColor={colors.background} />
      <AppNavigator />
    </SafeAreaProvider>
  );
}
