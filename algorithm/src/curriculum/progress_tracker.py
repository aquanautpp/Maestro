"""Progress tracking for the curriculum.

Tracks lesson completion, achievements earned,
and daily challenge streaks.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from dataclasses import dataclass, asdict, field


@dataclass
class CurriculumProgress:
    """Progress through the curriculum."""
    current_week: int = 1
    current_lesson: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    lessons_completed: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    daily_challenges_completed: int = 0
    last_challenge_date: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CurriculumProgress":
        return cls(
            current_week=data.get("current_week", 1),
            current_lesson=data.get("current_lesson"),
            started_at=data.get("started_at", datetime.now().isoformat()),
            lessons_completed=data.get("lessons_completed", []),
            achievements=data.get("achievements", []),
            daily_challenges_completed=data.get("daily_challenges_completed", 0),
            last_challenge_date=data.get("last_challenge_date"),
        )


class ProgressTracker:
    """
    Tracks progress through the curriculum.

    Stores progress locally for offline-first operation.
    """

    def __init__(self, progress_path: Optional[Path] = None):
        """
        Initialize progress tracker.

        Args:
            progress_path: Path to progress JSON file
        """
        if progress_path is None:
            progress_path = Path(__file__).parent.parent.parent / "data" / "curriculum_progress.json"

        self.progress_path = progress_path
        self._progress: Optional[CurriculumProgress] = None

    @property
    def progress(self) -> CurriculumProgress:
        """Lazy-load progress."""
        if self._progress is None:
            self._progress = self._load_progress()
        return self._progress

    def _load_progress(self) -> CurriculumProgress:
        """Load progress from file."""
        if not self.progress_path.exists():
            return CurriculumProgress()

        try:
            with open(self.progress_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CurriculumProgress.from_dict(data)
        except Exception:
            return CurriculumProgress()

    def _save_progress(self):
        """Save progress to file."""
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.progress_path, "w", encoding="utf-8") as f:
            json.dump(self.progress.to_dict(), f, indent=2, ensure_ascii=False)

    def get_current_state(self) -> Dict[str, Any]:
        """
        Get current curriculum state.

        Returns:
            Current progress state
        """
        progress = self.progress

        # Calculate week progress
        week_lessons = [l for l in progress.lessons_completed if l.startswith(f"{progress.current_week}.")]
        total_lessons_in_week = 2  # Assuming 2 lessons per week

        return {
            "current_week": progress.current_week,
            "current_lesson": progress.current_lesson,
            "started_at": progress.started_at,
            "lessons_completed_total": len(progress.lessons_completed),
            "lessons_completed_this_week": len(week_lessons),
            "total_lessons_this_week": total_lessons_in_week,
            "week_progress_percent": round(len(week_lessons) / total_lessons_in_week * 100),
            "achievements": progress.achievements,
            "daily_challenges_completed": progress.daily_challenges_completed,
        }

    def complete_lesson(self, lesson_id: str) -> Dict[str, Any]:
        """
        Mark a lesson as complete.

        Args:
            lesson_id: Lesson ID (e.g., "1.1")

        Returns:
            Updated progress state
        """
        progress = self.progress

        if lesson_id not in progress.lessons_completed:
            progress.lessons_completed.append(lesson_id)

        # Update current lesson to next
        week = int(lesson_id.split(".")[0])
        lesson_num = int(lesson_id.split(".")[1])

        # Check if week is complete
        week_lessons = [l for l in progress.lessons_completed if l.startswith(f"{week}.")]
        week_complete = len(week_lessons) >= 2  # Assuming 2 lessons per week

        if week_complete and week < 5:
            # Award achievement and advance week
            achievement_name = f"week_{week}_complete"
            if achievement_name not in progress.achievements:
                progress.achievements.append(achievement_name)
            progress.current_week = week + 1
            progress.current_lesson = f"{week + 1}.1"
        else:
            # Move to next lesson in week
            progress.current_lesson = f"{week}.{lesson_num + 1}"

        self._save_progress()

        return {
            "status": "completed",
            "lesson_id": lesson_id,
            "week_complete": week_complete,
            "new_achievement": achievement_name if week_complete and week < 5 else None,
            "progress": self.get_current_state(),
        }

    def complete_daily_challenge(self) -> Dict[str, Any]:
        """
        Mark today's daily challenge as complete.

        Returns:
            Updated challenge status
        """
        progress = self.progress
        today = date.today().isoformat()

        # Check if already completed today
        if progress.last_challenge_date == today:
            return {
                "status": "already_completed",
                "message": "Voce ja completou o desafio de hoje!",
            }

        progress.daily_challenges_completed += 1
        progress.last_challenge_date = today

        self._save_progress()

        return {
            "status": "completed",
            "total_challenges": progress.daily_challenges_completed,
            "message": "Desafio do dia completo!",
        }

    def get_achievements(self) -> List[Dict[str, Any]]:
        """
        Get all earned achievements.

        Returns:
            List of achievement dictionaries
        """
        achievements = []

        achievement_definitions = {
            "week_1_complete": {"name": "Observador Atento", "icon": "👀", "description": "Completou Semana 1"},
            "week_2_complete": {"name": "Encorajador", "icon": "💪", "description": "Completou Semana 2"},
            "week_3_complete": {"name": "Narrador", "icon": "🗣️", "description": "Completou Semana 3"},
            "week_4_complete": {"name": "Paciente", "icon": "⏳", "description": "Completou Semana 4"},
            "week_5_complete": {"name": "Mestre das Transicoes", "icon": "🔄", "description": "Completou Semana 5"},
            "all_complete": {"name": "Especialista Serve-and-Return", "icon": "🏆", "description": "Completou todo o curriculo"},
        }

        for ach_id in self.progress.achievements:
            definition = achievement_definitions.get(ach_id, {"name": ach_id, "icon": "⭐"})
            achievements.append({
                "id": ach_id,
                "earned_at": None,  # Could track this
                **definition,
            })

        # Check for completion achievement
        if len(self.progress.lessons_completed) >= 10:  # 5 weeks * 2 lessons
            if "all_complete" not in self.progress.achievements:
                self.progress.achievements.append("all_complete")
                self._save_progress()
                achievements.append({
                    "id": "all_complete",
                    **achievement_definitions["all_complete"],
                })

        return achievements

    def get_daily_challenge_status(self) -> Dict[str, Any]:
        """
        Get status of daily challenges.

        Returns:
            Challenge status
        """
        progress = self.progress
        today = date.today().isoformat()

        return {
            "completed_today": progress.last_challenge_date == today,
            "total_completed": progress.daily_challenges_completed,
            "current_week": progress.current_week,
        }

    def reset_progress(self) -> Dict[str, Any]:
        """
        Reset all progress (for testing or starting over).

        Returns:
            Confirmation message
        """
        self._progress = CurriculumProgress()
        self._save_progress()

        return {
            "status": "reset",
            "message": "Progresso reiniciado. Boa sorte na nova jornada!",
        }
