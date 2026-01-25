/**
 * Local notifications service.
 * Shows positive session summaries to encourage parents.
 */

import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { SessionSummary } from '../types';

// Configure notification handler
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

// ============================================================================
// Permissions
// ============================================================================

export async function requestNotificationPermissions(): Promise<boolean> {
  try {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    return finalStatus === 'granted';
  } catch (error) {
    console.error('Error requesting notification permissions:', error);
    return false;
  }
}

// ============================================================================
// Session Summary Notification
// ============================================================================

// Positive messages based on performance
const MESSAGES = {
  excellent: [
    'Incrível! Vocês tiveram {turns} conversational turns!',
    'Ótimo trabalho! {turns} interações hoje!',
    'Maravilha! {turns} trocas de conversa!',
  ],
  good: [
    'Muito bem! {turns} conversational turns!',
    'Boa sessão! {turns} interações!',
    'Legal! Vocês conversaram {turns} vezes!',
  ],
  encouraging: [
    'Bom começo! {turns} trocas de conversa.',
    'Cada conversa conta! {turns} interações.',
    'Continue assim! {turns} turns hoje.',
  ],
};

function getRandomMessage(category: keyof typeof MESSAGES, turns: number): string {
  const messages = MESSAGES[category];
  const message = messages[Math.floor(Math.random() * messages.length)];
  return message.replace('{turns}', turns.toString());
}

export async function showSessionSummaryNotification(
  summary: SessionSummary
): Promise<void> {
  const hasPermission = await requestNotificationPermissions();
  if (!hasPermission) return;

  const totalTurns = summary.totalServes + summary.totalReturns;

  // Choose message category based on performance
  let category: keyof typeof MESSAGES;
  if (summary.responseRate >= 0.7 && totalTurns >= 10) {
    category = 'excellent';
  } else if (summary.responseRate >= 0.5 || totalTurns >= 5) {
    category = 'good';
  } else {
    category = 'encouraging';
  }

  const title = '🌟 Sessão finalizada!';
  const body = getRandomMessage(category, totalTurns);

  await Notifications.scheduleNotificationAsync({
    content: {
      title,
      body,
      data: { type: 'session_summary', summary },
    },
    trigger: null, // Show immediately
  });
}

// ============================================================================
// Reminder Notifications
// ============================================================================

export async function scheduleDailyReminder(
  hour: number = 18,
  minute: number = 0
): Promise<void> {
  const hasPermission = await requestNotificationPermissions();
  if (!hasPermission) return;

  // Cancel existing reminders
  await cancelDailyReminder();

  await Notifications.scheduleNotificationAsync({
    content: {
      title: '💬 Hora de conversar!',
      body: 'Que tal uma sessão de conversação com seu filho?',
      data: { type: 'daily_reminder' },
    },
    trigger: {
      hour,
      minute,
      repeats: true,
    },
  });
}

export async function cancelDailyReminder(): Promise<void> {
  const scheduled = await Notifications.getAllScheduledNotificationsAsync();
  for (const notification of scheduled) {
    if (notification.content.data?.type === 'daily_reminder') {
      await Notifications.cancelScheduledNotificationAsync(notification.identifier);
    }
  }
}

// ============================================================================
// Cancel All
// ============================================================================

export async function cancelAllNotifications(): Promise<void> {
  await Notifications.cancelAllScheduledNotificationsAsync();
}
