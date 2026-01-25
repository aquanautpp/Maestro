/**
 * Weekly Summary Screen
 *
 * Shows a chart of conversational turns over the last 7 days.
 */

import React, { useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Dimensions,
} from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import { colors, spacing, fontSizes, borderRadius, shadows } from '../theme';
import { Card } from '../components';
import { useSession } from '../hooks';

const screenWidth = Dimensions.get('window').width;

export function WeeklyScreen() {
  const { dailyStats } = useSession();

  // Prepare chart data
  const chartData = useMemo(() => {
    const labels = dailyStats.map((day) => {
      const date = new Date(day.date);
      const weekday = date.toLocaleDateString('pt-BR', { weekday: 'short' });
      return weekday.charAt(0).toUpperCase() + weekday.slice(1, 3);
    });

    const data = dailyStats.map((day) => day.totalServes + day.totalReturns);

    return {
      labels,
      datasets: [{ data: data.length > 0 ? data : [0] }],
    };
  }, [dailyStats]);

  // Calculate weekly totals
  const weeklyTotals = useMemo(() => {
    const totalTurns = dailyStats.reduce(
      (sum, day) => sum + day.totalServes + day.totalReturns,
      0
    );
    const totalSessions = dailyStats.reduce(
      (sum, day) => sum + day.totalSessions,
      0
    );
    const totalMinutes = dailyStats.reduce(
      (sum, day) => sum + day.totalMinutes,
      0
    );
    const avgResponseRate =
      dailyStats.length > 0
        ? dailyStats.reduce((sum, day) => sum + day.responseRate, 0) /
          dailyStats.length
        : 0;

    return {
      totalTurns,
      totalSessions,
      totalMinutes: Math.round(totalMinutes),
      avgResponseRate: Math.round(avgResponseRate * 100),
    };
  }, [dailyStats]);

  // Find best day
  const bestDay = useMemo(() => {
    if (dailyStats.length === 0) return null;

    let best = dailyStats[0];
    for (const day of dailyStats) {
      if (day.totalServes + day.totalReturns > best.totalServes + best.totalReturns) {
        best = day;
      }
    }

    const date = new Date(best.date);
    return {
      weekday: date.toLocaleDateString('pt-BR', { weekday: 'long' }),
      turns: best.totalServes + best.totalReturns,
    };
  }, [dailyStats]);

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Semana</Text>
          <Text style={styles.subtitle}>Últimos 7 dias</Text>
        </View>

        {/* Chart */}
        <Card style={styles.chartCard}>
          <Text style={styles.chartTitle}>Conversational Turns</Text>
          <LineChart
            data={chartData}
            width={screenWidth - spacing.lg * 4}
            height={200}
            yAxisSuffix=""
            yAxisInterval={1}
            chartConfig={{
              backgroundColor: colors.surface,
              backgroundGradientFrom: colors.surface,
              backgroundGradientTo: colors.surface,
              decimalPlaces: 0,
              color: (opacity = 1) => `rgba(76, 175, 80, ${opacity})`,
              labelColor: (opacity = 1) => `rgba(94, 107, 94, ${opacity})`,
              style: {
                borderRadius: borderRadius.md,
              },
              propsForDots: {
                r: '6',
                strokeWidth: '2',
                stroke: colors.primary,
              },
              propsForBackgroundLines: {
                strokeDasharray: '',
                stroke: colors.chartGrid,
                strokeWidth: 1,
              },
            }}
            bezier
            style={styles.chart}
            withInnerLines={true}
            withOuterLines={false}
            withVerticalLines={false}
            fromZero
          />
        </Card>

        {/* Stats Grid */}
        <View style={styles.statsGrid}>
          <Card style={styles.statCard}>
            <Text style={styles.statValue}>{weeklyTotals.totalTurns}</Text>
            <Text style={styles.statLabel}>turns totais</Text>
          </Card>

          <Card style={styles.statCard}>
            <Text style={styles.statValue}>{weeklyTotals.totalSessions}</Text>
            <Text style={styles.statLabel}>sessões</Text>
          </Card>

          <Card style={styles.statCard}>
            <Text style={styles.statValue}>{weeklyTotals.totalMinutes}</Text>
            <Text style={styles.statLabel}>minutos</Text>
          </Card>

          <Card style={styles.statCard}>
            <Text style={styles.statValue}>{weeklyTotals.avgResponseRate}%</Text>
            <Text style={styles.statLabel}>taxa de resposta</Text>
          </Card>
        </View>

        {/* Best Day */}
        {bestDay && bestDay.turns > 0 && (
          <Card style={styles.bestDayCard}>
            <Text style={styles.bestDayTitle}>🌟 Melhor dia</Text>
            <Text style={styles.bestDayText}>
              {bestDay.weekday}: {bestDay.turns} turns
            </Text>
          </Card>
        )}

        {/* Empty State */}
        {weeklyTotals.totalTurns === 0 && (
          <Card style={styles.emptyCard}>
            <Text style={styles.emptyTitle}>Nenhum dado ainda</Text>
            <Text style={styles.emptyText}>
              Comece uma sessão para ver seus dados aqui!
            </Text>
          </Card>
        )}

        {/* Encouragement */}
        {weeklyTotals.totalTurns > 0 && (
          <Text style={styles.encouragement}>
            Cada conversa faz diferença! Continue assim! 💪
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
  title: {
    fontSize: fontSizes.xxl,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  subtitle: {
    fontSize: fontSizes.md,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },

  // Chart
  chartCard: {
    marginBottom: spacing.lg,
  },
  chartTitle: {
    fontSize: fontSizes.md,
    fontWeight: '600',
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  chart: {
    marginVertical: spacing.sm,
    borderRadius: borderRadius.md,
  },

  // Stats Grid
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginBottom: spacing.lg,
  },
  statCard: {
    width: (screenWidth - spacing.lg * 2 - spacing.md) / 2 - spacing.md / 2,
    alignItems: 'center',
    padding: spacing.md,
  },
  statValue: {
    fontSize: fontSizes.xl,
    fontWeight: '700',
    color: colors.primary,
  },
  statLabel: {
    fontSize: fontSizes.sm,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },

  // Best Day
  bestDayCard: {
    backgroundColor: colors.primaryLight,
    marginBottom: spacing.lg,
  },
  bestDayTitle: {
    fontSize: fontSizes.lg,
    fontWeight: '600',
    color: colors.textOnPrimary,
    marginBottom: spacing.xs,
  },
  bestDayText: {
    fontSize: fontSizes.md,
    color: colors.textOnPrimary,
  },

  // Empty State
  emptyCard: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
  },
  emptyTitle: {
    fontSize: fontSizes.lg,
    fontWeight: '600',
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  emptyText: {
    fontSize: fontSizes.md,
    color: colors.textMuted,
    textAlign: 'center',
  },

  // Encouragement
  encouragement: {
    textAlign: 'center',
    fontSize: fontSizes.md,
    color: colors.textSecondary,
  },
});
