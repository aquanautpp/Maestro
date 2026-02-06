"""Curriculum module management for the 5-week program.

Each week focuses on one serve-and-return step:
- Week 1: Share the Focus (observe child's interest)
- Week 2: Support and Encourage
- Week 3: Name It (build vocabulary)
- Week 4: Take Turns (wait for response)
- Week 5: Practice Endings (transitions)
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class CurriculumManager:
    """
    Manages the 5-week curriculum for parents.

    Provides lessons, activities, and daily challenges
    for each week of the program.
    """

    def __init__(self, curriculum_dir: Optional[Path] = None):
        """
        Initialize curriculum manager.

        Args:
            curriculum_dir: Directory containing curriculum JSON files
        """
        if curriculum_dir is None:
            curriculum_dir = Path(__file__).parent.parent.parent / "content" / "curriculum"

        self.curriculum_dir = curriculum_dir
        self._weeks: Dict[int, Dict] = {}

    def _load_week(self, week_num: int) -> Dict:
        """Load curriculum for a specific week."""
        if week_num in self._weeks:
            return self._weeks[week_num]

        filepath = self.curriculum_dir / f"week_{week_num}.json"

        if not filepath.exists():
            # Return default structure if file doesn't exist
            self._weeks[week_num] = self._get_default_week(week_num)
        else:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    self._weeks[week_num] = json.load(f)
            except Exception:
                self._weeks[week_num] = self._get_default_week(week_num)

        return self._weeks[week_num]

    def _get_default_week(self, week_num: int) -> Dict:
        """Get default curriculum for a week if file missing."""
        defaults = {
            1: {
                "week": 1,
                "title": "Compartilhe o Foco",
                "serve_return_step": 1,
                "description": "Aprenda a observar o que chama a atencao do seu filho",
                "lessons": [
                    {"id": "1.1", "title": "O que e 'serve'?", "content": "Quando seu filho olha, aponta ou balbucia - ele esta iniciando uma conversa!"},
                    {"id": "1.2", "title": "Seguindo o olhar", "content": "Observe para onde seu filho olha e olhe junto."},
                ],
                "daily_challenges": [
                    "Observe 3 coisas que chamam a atencao do seu filho hoje",
                    "Siga o olhar do seu filho por 2 minutos durante uma brincadeira",
                ],
                "goal": "Observe 5 momentos de interesse da crianca esta semana",
                "achievement": {"name": "Observador Atento", "icon": "👀"},
            },
            2: {
                "week": 2,
                "title": "Apoie e Encoraje",
                "serve_return_step": 2,
                "description": "Responda ao seu filho com calor e encorajamento",
                "lessons": [
                    {"id": "2.1", "title": "O poder do sorriso", "content": "Seu sorriso diz ao seu filho que ele e importante."},
                    {"id": "2.2", "title": "Tom de voz", "content": "Use um tom animado e caloroso quando responder."},
                ],
                "daily_challenges": [
                    "Sorria 10 vezes para seu filho hoje",
                    "Use expressoes animadas quando ele mostrar algo",
                ],
                "goal": "Responda com encorajamento a cada 'serve' do seu filho",
                "achievement": {"name": "Encorajador", "icon": "💪"},
            },
            3: {
                "week": 3,
                "title": "Nomeie o Mundo",
                "serve_return_step": 3,
                "description": "Construa vocabulario nomeando o que voces veem juntos",
                "lessons": [
                    {"id": "3.1", "title": "Narrador da vida real", "content": "Descreva o que voces estao fazendo juntos."},
                    {"id": "3.2", "title": "Expandindo palavras", "content": "Se ele diz 'au au', voce diz 'Sim, o cachorro grande!'"},
                ],
                "daily_challenges": [
                    "Nomeie 5 objetos novos hoje",
                    "Narre uma atividade inteira (vestir, comer, brincar)",
                ],
                "goal": "Nomeie pelo menos 10 coisas por dia",
                "achievement": {"name": "Narrador", "icon": "🗣️"},
            },
            4: {
                "week": 4,
                "title": "Espere a Vez",
                "serve_return_step": 4,
                "description": "De tempo para seu filho responder",
                "lessons": [
                    {"id": "4.1", "title": "Conte ate 5", "content": "Depois de falar, conte mentalmente ate 5 antes de falar de novo."},
                    {"id": "4.2", "title": "Silencio produtivo", "content": "O silencio da tempo para o cerebro processar."},
                ],
                "daily_challenges": [
                    "Faca uma pergunta e espere 5 segundos pela resposta",
                    "Deixe seu filho liderar uma brincadeira por 5 minutos",
                ],
                "goal": "Pratique pausas em todas as conversas",
                "achievement": {"name": "Paciente", "icon": "⏳"},
            },
            5: {
                "week": 5,
                "title": "Pratique Transicoes",
                "serve_return_step": 5,
                "description": "Ajude seu filho a navegar mudancas de atividade",
                "lessons": [
                    {"id": "5.1", "title": "Avisos previos", "content": "Avise antes de mudar: 'Mais 2 minutinhos e vamos...'"},
                    {"id": "5.2", "title": "Descrevendo o proximo passo", "content": "Diga o que vem depois: 'Agora vamos guardar e depois lanchar!'"},
                ],
                "daily_challenges": [
                    "Avise com 2 minutos de antecedencia antes de cada transicao",
                    "Descreva 3 transicoes do dia para seu filho",
                ],
                "goal": "Faca transicoes suaves em todas as atividades",
                "achievement": {"name": "Mestre das Transicoes", "icon": "🔄"},
            },
        }
        return defaults.get(week_num, {"week": week_num, "title": f"Semana {week_num}", "lessons": []})

    def get_week(self, week_num: int) -> Dict:
        """
        Get curriculum for a specific week.

        Args:
            week_num: Week number (1-5)

        Returns:
            Week curriculum dictionary
        """
        if not 1 <= week_num <= 5:
            return {"error": "Week must be 1-5"}

        return self._load_week(week_num)

    def get_lesson(self, week_num: int, lesson_id: str) -> Optional[Dict]:
        """
        Get a specific lesson.

        Args:
            week_num: Week number
            lesson_id: Lesson ID (e.g., "1.1")

        Returns:
            Lesson dictionary or None
        """
        week = self.get_week(week_num)
        for lesson in week.get("lessons", []):
            if lesson.get("id") == lesson_id:
                return lesson
        return None

    def get_daily_challenge(self, week_num: int, day: int = 0) -> Optional[str]:
        """
        Get daily challenge for a week.

        Args:
            week_num: Week number
            day: Day index (0-based, cycles through available challenges)

        Returns:
            Challenge string or None
        """
        week = self.get_week(week_num)
        challenges = week.get("daily_challenges", [])

        if not challenges:
            return None

        return challenges[day % len(challenges)]

    def get_achievement(self, week_num: int) -> Optional[Dict]:
        """
        Get achievement for completing a week.

        Args:
            week_num: Week number

        Returns:
            Achievement dictionary or None
        """
        week = self.get_week(week_num)
        return week.get("achievement")

    def get_curriculum_overview(self) -> List[Dict]:
        """
        Get overview of all weeks.

        Returns:
            List of week summaries
        """
        overview = []
        for week_num in range(1, 6):
            week = self.get_week(week_num)
            overview.append({
                "week": week_num,
                "title": week.get("title"),
                "serve_return_step": week.get("serve_return_step"),
                "description": week.get("description"),
                "lesson_count": len(week.get("lessons", [])),
                "achievement": week.get("achievement"),
            })
        return overview
