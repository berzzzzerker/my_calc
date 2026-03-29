from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class CalculatorConfig:
    energy_one_kg_fat: int = 7700
    protein_tef_rate: float = 0.25
    fat_tef_rate: float = 0.02
    carbs_tef_rate: float = 0.07

    default_step_kcal_per_kg: float = 0.0005
    default_training_kcal_per_hour_per_kg: float = 5.0

    history_file: str = "weight_history.csv"
    profiles_file: str = "profiles.json"


@dataclass
class UserInput:
    first_name: str = ""
    last_name: str = ""

    sex: str = "мужчина"
    current_weight: float = 0.0
    current_height: int = 0
    current_age: int = 0

    steps_per_day: int = 10000
    trainings_per_week: int = 3
    training_minutes: int = 60

    weekly_protein: float = 0.0
    weekly_fat: float = 0.0
    weekly_carbs: float = 0.0
    avg_kcal_per_day: float = 0.0

    goal_mode: str = "вес"
    goal_weight: float | None = None
    current_body_fat: float | None = None
    target_body_fat: float | None = None


@dataclass
class MacroBreakdown:
    protein_per_day: float
    fat_per_day: float
    carbs_per_day: float
    tef: float


@dataclass
class TDEEEstimate:
    formula_tdee: float
    fact_tdee: float
    explanation: str
    source_name: str


@dataclass
class GoalResult:
    goal_weight: float
    description: str
    goal_label: str


@dataclass
class ForecastResult:
    total_days: float
    weekly_loss_rate: float
    stopped_early: bool
    possible_loss: float
    final_deficit: float


class AppError(Exception):
    pass


class FileStorageHelper:
    @staticmethod
    def app_directory() -> Path:
        return Path(__file__).resolve().parent


class DateFormatterHelper:
    @staticmethod
    def timestamp_string(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")


class WeightLossCalculator:
    def __init__(self, config: CalculatorConfig):
        self.config = config

    def calculate(self, data: UserInput) -> dict:
        self.validate(data)

        bmr = self.calculate_bmr(data)
        macros = self.calculate_daily_macros_and_tef(data)
        formula_tdee = self.calculate_formula_tdee(data, bmr, macros.tef)
        tdee_estimate = self.calculate_tdee_estimate(formula_tdee)
        goal = self.calculate_goal(data)

        forecast = self.calculate_forecast(
            current_weight=data.current_weight,
            goal_weight=goal.goal_weight,
            tdee=tdee_estimate.fact_tdee,
            avg_kcal_per_day=data.avg_kcal_per_day,
        )

        current_deficit = round(tdee_estimate.fact_tdee - data.avg_kcal_per_day)
        maintenance = round(tdee_estimate.fact_tdee)
        status = self.get_deficit_status(current_deficit)

        protein_per_day = round(macros.protein_per_day, 1)
        fat_per_day = round(macros.fat_per_day, 1)
        carbs_per_day = round(macros.carbs_per_day, 1)

        lines = [
            "=== ОСНОВНОЙ РЕЗУЛЬТАТ ===",
            f"Профиль: {self.format_profile_name(data)}",
            f"Текущий дефицит: {current_deficit:.0f} ккал/день",
            f"Текущая норма ккал: {maintenance:.0f} ккал/день",
            f"Время для похудения: {self.format_goal_timeline(forecast)}",
            "",
            "=== ДОПОЛНИТЕЛЬНО ===",
            goal.description,
            f"BMR: {round(bmr):.0f} ккал",
            f"TDEE по формуле: {round(formula_tdee):.0f} ккал",
            f"Источник расчёта: {tdee_estimate.source_name}",
            "",
            "=== ПИТАНИЕ ===",
            f"Средние Б/Ж/У в день: {protein_per_day} / {fat_per_day} / {carbs_per_day} г",
            f"TEF: {round(macros.tef):.0f} ккал",
            f"Средний рацион: {round(data.avg_kcal_per_day):.0f} ккал/день",
            "",
            "=== ОЦЕНКА TDEE ===",
            tdee_estimate.explanation,
            f"Фактический TDEE для расчёта: {round(tdee_estimate.fact_tdee):.0f} ккал",
        ]

        return {
            "profile_name": self.format_profile_name(data),
            "deficit": current_deficit,
            "maintenance": maintenance,
            "goal_text": goal.goal_label,
            "goal_description": goal.description,
            "bmr": round(bmr),
            "tdee": round(formula_tdee),
            "timeline": self.format_goal_timeline(forecast),
            "status": status,
            "output_text": "\n".join(lines),
            "meta": {
                "protein_per_day": protein_per_day,
                "fat_per_day": fat_per_day,
                "carbs_per_day": carbs_per_day,
                "tef": round(macros.tef),
            },
        }

    def format_profile_name(self, data: UserInput) -> str:
        full_name = f"{data.first_name.strip()} {data.last_name.strip()}".strip()
        return full_name if full_name else "Без имени"

    def validate(self, data: UserInput) -> None:
        if data.sex not in ("мужчина", "женщина"):
            raise AppError("Пол должен быть: мужчина или женщина.")

        numeric_positive = [
            ("Текущий вес", data.current_weight),
            ("Рост", float(data.current_height)),
            ("Возраст", float(data.current_age)),
            ("Средние ккал", data.avg_kcal_per_day),
            ("Минут в тренировке", float(data.training_minutes)),
        ]
        for field_name, value in numeric_positive:
            if value <= 0:
                raise AppError(f"{field_name} должно быть больше 0.")

        numeric_non_negative = [
            ("Шаги", float(data.steps_per_day)),
            ("Тренировки в неделю", float(data.trainings_per_week)),
            ("Белки за неделю", data.weekly_protein),
            ("Жиры за неделю", data.weekly_fat),
            ("Углеводы за неделю", data.weekly_carbs),
        ]
        for field_name, value in numeric_non_negative:
            if value < 0:
                raise AppError(f"{field_name} не может быть отрицательным.")

        if data.goal_mode not in ("вес", "жир"):
            raise AppError("Способ задания цели заполнен некорректно.")

        if data.goal_mode == "вес":
            if data.goal_weight is None:
                raise AppError("Укажи целевой вес.")
            if data.goal_weight <= 0:
                raise AppError("Целевой вес должен быть больше 0.")
            if data.goal_weight >= data.current_weight:
                raise AppError("Целевой вес должен быть меньше текущего.")

        if data.goal_mode == "жир":
            if data.current_body_fat is None or data.target_body_fat is None:
                raise AppError("Для цели по жиру нужно указать текущий и целевой % жира.")

            current_body_fat = data.current_body_fat
            target_body_fat = data.target_body_fat
            if not (0 < current_body_fat < 100 and 0 < target_body_fat < 100):
                raise AppError("% жира должен быть в диапазоне 0-100.")
            if target_body_fat >= current_body_fat:
                raise AppError("Целевой % жира должен быть меньше текущего.")

    def calculate_bmr(self, data: UserInput) -> float:
        sex_constant = 5.0 if data.sex == "мужчина" else -161.0
        return 10 * data.current_weight + 6.25 * data.current_height - 5 * data.current_age + sex_constant

    def calculate_daily_macros_and_tef(self, data: UserInput) -> MacroBreakdown:
        protein = data.weekly_protein / 7.0
        fat = data.weekly_fat / 7.0
        carbs = data.weekly_carbs / 7.0

        protein_tef = protein * 4 * self.config.protein_tef_rate
        fat_tef = fat * 9 * self.config.fat_tef_rate
        carbs_tef = carbs * 4 * self.config.carbs_tef_rate
        tef = protein_tef + fat_tef + carbs_tef

        return MacroBreakdown(
            protein_per_day=protein,
            fat_per_day=fat,
            carbs_per_day=carbs,
            tef=tef,
        )

    def calculate_formula_tdee(self, data: UserInput, bmr: float, tef: float) -> float:
        steps_kcal = data.steps_per_day * data.current_weight * self.config.default_step_kcal_per_kg

        training_hours_per_week = (data.trainings_per_week * data.training_minutes) / 60.0
        training_kcal_per_week = (
            training_hours_per_week
            * data.current_weight
            * self.config.default_training_kcal_per_hour_per_kg
        )
        training_kcal_per_day = training_kcal_per_week / 7.0

        return bmr + steps_kcal + training_kcal_per_day + tef

    def calculate_tdee_estimate(self, formula_tdee: float) -> TDEEEstimate:
        return TDEEEstimate(
            formula_tdee=formula_tdee,
            fact_tdee=formula_tdee,
            explanation="История веса отключена, поэтому расчёт идёт только по формуле.",
            source_name="формула",
        )

    def calculate_goal(self, data: UserInput) -> GoalResult:
        if data.goal_mode == "вес":
            if data.goal_weight is None:
                raise AppError("Укажи целевой вес.")
            return GoalResult(
                goal_weight=data.goal_weight,
                description=f"Цель по весу: {data.current_weight:.1f} → {data.goal_weight:.1f} кг",
                goal_label=f"{round(data.current_weight):.0f} → {round(data.goal_weight):.0f} кг",
            )

        if data.current_body_fat is None or data.target_body_fat is None:
            raise AppError("Для цели по жиру нужно указать текущий и целевой % жира.")

        lean_mass = data.current_weight * (1 - data.current_body_fat / 100.0)
        goal_weight = lean_mass / (1 - data.target_body_fat / 100.0)
        if goal_weight >= data.current_weight:
            raise AppError("Расчётный целевой вес вышел не меньше текущего.")

        return GoalResult(
            goal_weight=goal_weight,
            description=(
                f"Цель по жиру: {data.current_body_fat:.1f}% → {data.target_body_fat:.1f}%\n"
                f"Расчётный целевой вес: {goal_weight:.1f} кг"
            ),
            goal_label=f"{round(data.current_body_fat):.0f}% → {round(data.target_body_fat):.0f}%",
        )

    def calculate_forecast(
        self,
        current_weight: float,
        goal_weight: float,
        tdee: float,
        avg_kcal_per_day: float,
    ) -> ForecastResult:
        kg_remaining = current_weight - goal_weight
        if kg_remaining <= 0:
            raise AppError("До цели уже нечего снижать.")

        current_deficit = tdee - avg_kcal_per_day
        if current_deficit <= 0:
            return ForecastResult(
                total_days=0.0,
                weekly_loss_rate=0.0,
                stopped_early=True,
                possible_loss=0.0,
                final_deficit=current_deficit,
            )

        total_kcal_needed = kg_remaining * self.config.energy_one_kg_fat
        total_days = total_kcal_needed / current_deficit
        weekly_loss = (current_deficit * 7) / self.config.energy_one_kg_fat

        return ForecastResult(
            total_days=total_days,
            weekly_loss_rate=weekly_loss,
            stopped_early=False,
            possible_loss=kg_remaining,
            final_deficit=current_deficit,
        )

    def format_goal_timeline(self, forecast: ForecastResult) -> str:
        if forecast.stopped_early:
            return "цель не будет достигнута, потому что текущий дефицит отсутствует или равен нулю"

        weeks = forecast.total_days / 7.0
        months = forecast.total_days / 30.44
        return f"{round(forecast.total_days):.0f} дн. / {weeks:.1f} нед. / {months:.1f} мес."

    def get_deficit_status(self, deficit: float) -> dict:
        if deficit >= 600:
            return {
                "key": "green",
                "emoji": "😄",
                "title": "Дефицит высокий",
                "subtitle": f"Текущий дефицит {deficit:.0f} ккал. Это высокий дефицит.",
                "color": "#2e7d32",
            }
        if deficit >= 400:
            return {
                "key": "yellow",
                "emoji": "🙂",
                "title": "Дефицит средний",
                "subtitle": f"Текущий дефицит {deficit:.0f} ккал. Это средний дефицит.",
                "color": "#f9a825",
            }
        if deficit >= 200:
            return {
                "key": "orange",
                "emoji": "😐",
                "title": "Дефицит низкий",
                "subtitle": f"Текущий дефицит {deficit:.0f} ккал. Это низкий дефицит.",
                "color": "#ef6c00",
            }
        return {
            "key": "red",
            "emoji": "☹️",
            "title": "Дефицит низкий",
            "subtitle": f"Текущий дефицит {deficit:.0f} ккал. Это почти поддержание.",
            "color": "#c62828",
        }


class HistoryStorage:
    def __init__(self, file_name: str):
        self.file_path = FileStorageHelper.app_directory() / file_name

    def append_record(self, data: UserInput) -> None:
        file_exists = self.file_path.exists()

        with self.file_path.open("a", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            if not file_exists:
                writer.writerow([
                    "saved_at",
                    "first_name",
                    "last_name",
                    "sex",
                    "current_weight",
                    "height",
                    "age",
                    "steps_per_day",
                    "trainings_per_week",
                    "training_minutes",
                    "weekly_protein",
                    "weekly_fat",
                    "weekly_carbs",
                    "avg_kcal_per_day",
                    "goal_mode",
                    "goal_weight",
                    "current_body_fat",
                    "target_body_fat",
                ])
            writer.writerow([
                DateFormatterHelper.timestamp_string(datetime.now()),
                data.first_name,
                data.last_name,
                data.sex,
                data.current_weight,
                data.current_height,
                data.current_age,
                data.steps_per_day,
                data.trainings_per_week,
                data.training_minutes,
                data.weekly_protein,
                data.weekly_fat,
                data.weekly_carbs,
                data.avg_kcal_per_day,
                data.goal_mode,
                data.goal_weight,
                data.current_body_fat,
                data.target_body_fat,
            ])

    def download_file(self):
        if not self.file_path.exists():
            raise AppError("История ещё не создана.")
        return self.file_path


class ProfileStorage:
    def __init__(self, file_name: str):
        self.file_path = FileStorageHelper.app_directory() / file_name

    def read_all(self) -> dict[str, UserInput]:
        if not self.file_path.exists():
            return {}
        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8"))
            return {key: UserInput(**value) for key, value in raw.items()}
        except Exception:
            return {}

    def write_all(self, data: dict[str, UserInput]) -> None:
        serializable = {key: asdict(value) for key, value in data.items()}
        self.file_path.write_text(
            json.dumps(serializable, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    @staticmethod
    def make_key(first_name: str, last_name: str) -> str:
        return f"{first_name.strip()} {last_name.strip()}".strip()

    def list_profiles(self) -> list[str]:
        return sorted(self.read_all().keys(), key=str.lower)

    def save_profile(self, data: UserInput) -> str:
        key = self.make_key(data.first_name, data.last_name)
        if not key:
            raise AppError("Чтобы сохранить профиль, укажи Имя и Фамилию.")

        all_profiles = self.read_all()
        all_profiles[key] = data
        self.write_all(all_profiles)
        return key

    def load_profile(self, profile_name: str) -> UserInput | None:
        return self.read_all().get(profile_name)

    def delete_profile(self, profile_name: str) -> bool:
        all_profiles = self.read_all()
        if profile_name not in all_profiles:
            return False
        del all_profiles[profile_name]
        self.write_all(all_profiles)
        return True
