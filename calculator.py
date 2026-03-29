from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import csv
import json


class AppError(Exception):
    """Ошибки валидации и доменной логики приложения."""


@dataclass
class CalculatorConfig:
    history_file: str = "weight_history.csv"
    profiles_file: str = "profiles.json"


@dataclass
class UserInput:
    first_name: str
    last_name: str
    sex: str
    current_weight: float
    current_height: int
    current_age: int
    steps_per_day: int
    trainings_per_week: int
    training_minutes: int
    weekly_protein: float
    weekly_fat: float
    weekly_carbs: float
    avg_kcal_per_day: float
    goal_mode: str
    goal_weight: float | None = None
    current_body_fat: float | None = None
    target_body_fat: float | None = None


class WeightLossCalculator:
    def __init__(self, config: CalculatorConfig):
        self.config = config

    @staticmethod
    def _bmr(data: UserInput) -> int:
        if data.current_weight <= 0 or data.current_height <= 0 or data.current_age <= 0:
            raise AppError("Для расчёта BMR укажи корректные вес, рост и возраст.")
        base = 10 * data.current_weight + 6.25 * data.current_height - 5 * data.current_age
        return round(base + (-161 if data.sex == "женщина" else 5))

    @staticmethod
    def _tdee(data: UserInput, bmr: int) -> int:
        step_calories = data.steps_per_day * max(data.current_weight, 1) * 0.0005
        workout_daily = (data.trainings_per_week * data.training_minutes * 6) / 7
        return round(bmr + step_calories + workout_daily)

    def calculate(self, data: UserInput) -> dict:
        bmr = self._bmr(data)
        tdee = self._tdee(data, bmr)
        deficit = max(0, round(tdee - data.avg_kcal_per_day))

        result = {
            "bmr": bmr,
            "tdee": tdee,
            "deficit": deficit,
            "status": "good" if deficit >= 500 else "mid" if deficit >= 200 else "bad",
        }

        if data.goal_mode == "вес" and data.goal_weight is not None and 0 < data.goal_weight < data.current_weight:
            kg_to_lose = data.current_weight - data.goal_weight
            if deficit <= 0:
                result["time_to_goal"] = "Нужен дефицит калорий для расчёта срока"
            else:
                days = int((kg_to_lose * 7700 + deficit - 1) // deficit)
                result["time_to_goal"] = {"days": days, "weeks": (days + 6) // 7}
        elif data.goal_mode == "жир" and data.target_body_fat is not None:
            result["time_to_goal"] = "Цель по % жира оценивай по динамике замеров каждую неделю"

        return result


class HistoryStorage:
    _fields = [
        "date",
        "name",
        "sex",
        "weight",
        "height",
        "age",
        "steps",
        "workouts",
        "minutes_per_workout",
        "protein_week",
        "fat_week",
        "carbs_week",
        "avg_kcal_per_day",
        "goal_mode",
        "goal_weight",
        "current_body_fat",
        "target_body_fat",
    ]

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def _ensure_file(self) -> None:
        if self.file_path.exists():
            return
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=self._fields)
            writer.writeheader()

    def append_record(self, data: UserInput) -> None:
        self._ensure_file()
        with self.file_path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=self._fields)
            writer.writerow(
                {
                    "date": datetime.now(timezone.utc).isoformat(),
                    "name": f"{data.first_name} {data.last_name}".strip(),
                    "sex": data.sex,
                    "weight": data.current_weight,
                    "height": data.current_height,
                    "age": data.current_age,
                    "steps": data.steps_per_day,
                    "workouts": data.trainings_per_week,
                    "minutes_per_workout": data.training_minutes,
                    "protein_week": data.weekly_protein,
                    "fat_week": data.weekly_fat,
                    "carbs_week": data.weekly_carbs,
                    "avg_kcal_per_day": data.avg_kcal_per_day,
                    "goal_mode": data.goal_mode,
                    "goal_weight": data.goal_weight,
                    "current_body_fat": data.current_body_fat,
                    "target_body_fat": data.target_body_fat,
                }
            )

    def download_file(self) -> str:
        self._ensure_file()
        return str(self.file_path)


class ProfileStorage:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def _read_all(self) -> dict[str, dict]:
        if not self.file_path.exists():
            return {}
        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError as exc:
            raise AppError("profiles.json повреждён и не читается") from exc
        return raw if isinstance(raw, dict) else {}

    def _write_all(self, payload: dict[str, dict]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _profile_name(data: UserInput) -> str:
        full_name = f"{data.first_name} {data.last_name}".strip()
        return full_name or "Профиль без имени"

    def save_profile(self, data: UserInput) -> str:
        name = self._profile_name(data)
        profiles = self._read_all()
        profiles[name] = asdict(data)
        self._write_all(profiles)
        return name

    def list_profiles(self) -> list[str]:
        return sorted(self._read_all().keys())

    def load_profile(self, profile_name: str) -> UserInput | None:
        profile = self._read_all().get(profile_name)
        if profile is None:
            return None
        return UserInput(**profile)

    def delete_profile(self, profile_name: str) -> bool:
        profiles = self._read_all()
        existed = profile_name in profiles
        if existed:
            profiles.pop(profile_name, None)
            self._write_all(profiles)
        return existed
