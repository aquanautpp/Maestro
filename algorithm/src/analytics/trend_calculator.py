"""Trend calculation for tracking progress over time.

Calculates rolling averages, week-over-week comparisons,
and streak tracking for engagement.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class TrendData:
    """Trend information for a metric."""
    metric: str
    current_value: float
    previous_value: Optional[float]
    change_percent: Optional[float]
    direction: str  # 'up', 'down', 'stable'
    period: str  # '7d', '30d', etc.

    def to_dict(self) -> dict:
        return asdict(self)


class TrendCalculator:
    """
    Calculates trends and progress metrics.

    Tracks:
    - Rolling averages (7-day, 30-day)
    - Week-over-week changes
    - Streaks (consecutive days with sessions)
    - Best performances
    """

    def __init__(self, sessions_dir: Optional[Path] = None):
        """
        Initialize trend calculator.

        Args:
            sessions_dir: Directory containing session JSON files
        """
        if sessions_dir is None:
            sessions_dir = Path(__file__).parent.parent.parent / "data" / "sessions"

        self.sessions_dir = sessions_dir

    def load_sessions_by_date(
        self,
        days: int = 90
    ) -> Dict[date, List[dict]]:
        """
        Load sessions grouped by date.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary of date -> list of sessions
        """
        if not self.sessions_dir.exists():
            return {}

        cutoff = datetime.now() - timedelta(days=days)
        sessions_by_date: Dict[date, List[dict]] = {}

        for filepath in self.sessions_dir.glob("*.json"):
            try:
                date_str = filepath.stem[:10]
                file_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                if datetime.combine(file_date, datetime.min.time()) >= cutoff:
                    with open(filepath, "r", encoding="utf-8") as f:
                        session = json.load(f)

                    if file_date not in sessions_by_date:
                        sessions_by_date[file_date] = []
                    sessions_by_date[file_date].append(session)

            except Exception:
                continue

        return sessions_by_date

    def calculate_daily_metrics(
        self,
        sessions_by_date: Dict[date, List[dict]]
    ) -> Dict[date, dict]:
        """
        Calculate daily aggregated metrics.

        Args:
            sessions_by_date: Sessions grouped by date

        Returns:
            Dictionary of date -> daily metrics
        """
        daily_metrics = {}

        for day, sessions in sessions_by_date.items():
            total_moments = sum(s.get("moments", 0) for s in sessions)
            total_duration = sum(s.get("duration_minutes", 0) for s in sessions)
            session_count = len(sessions)

            all_response_times = []
            for s in sessions:
                all_response_times.extend(s.get("response_times", []))

            avg_response = (
                sum(all_response_times) / len(all_response_times)
                if all_response_times else None
            )

            daily_metrics[day] = {
                "moments": total_moments,
                "duration_minutes": round(total_duration, 1),
                "sessions": session_count,
                "moments_per_hour": round(total_moments / (total_duration / 60), 1) if total_duration > 0 else 0,
                "avg_response_time": round(avg_response, 2) if avg_response else None,
            }

        return daily_metrics

    def calculate_rolling_average(
        self,
        daily_metrics: Dict[date, dict],
        metric: str,
        window: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Calculate rolling average for a metric.

        Args:
            daily_metrics: Daily metrics dictionary
            metric: Metric to average
            window: Window size in days

        Returns:
            List of date/value pairs for the rolling average
        """
        if not daily_metrics:
            return []

        sorted_dates = sorted(daily_metrics.keys())
        result = []

        for i, current_date in enumerate(sorted_dates):
            # Get values for the window
            window_values = []
            for j in range(max(0, i - window + 1), i + 1):
                day = sorted_dates[j]
                value = daily_metrics[day].get(metric)
                if value is not None:
                    window_values.append(value)

            if window_values:
                avg = sum(window_values) / len(window_values)
                result.append({
                    "date": current_date.isoformat(),
                    "value": round(avg, 2),
                    "window": window,
                })

        return result

    def calculate_week_over_week(
        self,
        daily_metrics: Dict[date, dict],
        metric: str
    ) -> TrendData:
        """
        Calculate week-over-week change for a metric.

        Args:
            daily_metrics: Daily metrics dictionary
            metric: Metric to compare

        Returns:
            TrendData with comparison
        """
        today = date.today()
        this_week_start = today - timedelta(days=7)
        last_week_start = today - timedelta(days=14)

        this_week = []
        last_week = []

        for day, metrics in daily_metrics.items():
            value = metrics.get(metric)
            if value is not None:
                if this_week_start <= day <= today:
                    this_week.append(value)
                elif last_week_start <= day < this_week_start:
                    last_week.append(value)

        current_value = sum(this_week) if this_week else 0
        previous_value = sum(last_week) if last_week else None

        if previous_value and previous_value > 0:
            change_percent = ((current_value - previous_value) / previous_value) * 100
        else:
            change_percent = None

        if change_percent is None:
            direction = "stable"
        elif change_percent > 5:
            direction = "up"
        elif change_percent < -5:
            direction = "down"
        else:
            direction = "stable"

        return TrendData(
            metric=metric,
            current_value=current_value,
            previous_value=previous_value,
            change_percent=round(change_percent, 1) if change_percent else None,
            direction=direction,
            period="7d",
        )

    def calculate_streak(
        self,
        sessions_by_date: Dict[date, List[dict]]
    ) -> Dict[str, Any]:
        """
        Calculate current and longest streak of consecutive days.

        Args:
            sessions_by_date: Sessions grouped by date

        Returns:
            Streak information
        """
        if not sessions_by_date:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "last_session_date": None,
            }

        sorted_dates = sorted(sessions_by_date.keys())

        # Calculate current streak (counting back from today)
        today = date.today()
        current_streak = 0
        check_date = today

        while check_date in sessions_by_date or (check_date == today and (today - timedelta(days=1)) in sessions_by_date):
            if check_date in sessions_by_date:
                current_streak += 1
                check_date -= timedelta(days=1)
            elif check_date == today:
                # Allow checking yesterday if no session today
                check_date -= timedelta(days=1)
            else:
                break

        # Calculate longest streak
        longest_streak = 0
        current_run = 0
        prev_date = None

        for d in sorted_dates:
            if prev_date is None or (d - prev_date).days == 1:
                current_run += 1
            else:
                longest_streak = max(longest_streak, current_run)
                current_run = 1
            prev_date = d

        longest_streak = max(longest_streak, current_run)

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "last_session_date": sorted_dates[-1].isoformat() if sorted_dates else None,
        }

    def get_best_performances(
        self,
        daily_metrics: Dict[date, dict]
    ) -> Dict[str, Any]:
        """
        Get best performance records.

        Args:
            daily_metrics: Daily metrics dictionary

        Returns:
            Dictionary of best performances
        """
        if not daily_metrics:
            return {}

        # Best day for moments
        best_moments_day = max(
            daily_metrics.items(),
            key=lambda x: x[1].get("moments", 0)
        )

        # Best day for moments per hour
        best_rate_day = max(
            daily_metrics.items(),
            key=lambda x: x[1].get("moments_per_hour", 0)
        )

        # Best response time (lowest)
        valid_response_days = [
            (d, m) for d, m in daily_metrics.items()
            if m.get("avg_response_time") is not None
        ]
        best_response_day = min(
            valid_response_days,
            key=lambda x: x[1]["avg_response_time"]
        ) if valid_response_days else None

        return {
            "best_moments": {
                "date": best_moments_day[0].isoformat(),
                "value": best_moments_day[1].get("moments", 0),
            },
            "best_rate": {
                "date": best_rate_day[0].isoformat(),
                "value": best_rate_day[1].get("moments_per_hour", 0),
            },
            "best_response_time": {
                "date": best_response_day[0].isoformat(),
                "value": best_response_day[1].get("avg_response_time"),
            } if best_response_day else None,
        }

    def get_full_trends(self, days: int = 90) -> Dict[str, Any]:
        """
        Get complete trend analysis.

        Args:
            days: Days to analyze

        Returns:
            Complete trends dictionary
        """
        sessions_by_date = self.load_sessions_by_date(days=days)

        if not sessions_by_date:
            return {
                "status": "no_data",
                "message": "Ainda nao ha sessoes para analisar.",
            }

        daily_metrics = self.calculate_daily_metrics(sessions_by_date)

        return {
            "status": "success",
            "days_analyzed": days,
            "total_days_with_sessions": len(sessions_by_date),
            "streak": self.calculate_streak(sessions_by_date),
            "week_over_week": {
                "moments": self.calculate_week_over_week(daily_metrics, "moments").to_dict(),
                "duration": self.calculate_week_over_week(daily_metrics, "duration_minutes").to_dict(),
            },
            "rolling_averages": {
                "moments_7d": self.calculate_rolling_average(daily_metrics, "moments", 7)[-7:],
                "moments_30d": self.calculate_rolling_average(daily_metrics, "moments", 30)[-30:],
            },
            "best_performances": self.get_best_performances(daily_metrics),
        }
