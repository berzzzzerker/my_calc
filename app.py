from __future__ import annotations

from dataclasses import asdict

from flask import Flask, jsonify, render_template, request, send_file

from calculator import (
    AppError,
    CalculatorConfig,
    HistoryStorage,
    ProfileStorage,
    UserInput,
    WeightLossCalculator,
)

app = Flask(__name__)
config = CalculatorConfig()
calculator = WeightLossCalculator(config)
history_storage = HistoryStorage(config.history_file)
profile_storage = ProfileStorage(config.profiles_file)


def normalize_sex(value: str) -> str:
    value = str(value or "").strip().lower()
    mapping = {
        "male": "мужчина",
        "female": "женщина",
        "мужчина": "мужчина",
        "женщина": "женщина",
    }
    return mapping.get(value, "мужчина")


def normalize_goal_mode(value: str) -> str:
    value = str(value or "").strip().lower()
    mapping = {
        "weight": "вес",
        "fat": "жир",
        "вес": "вес",
        "жир": "жир",
    }
    return mapping.get(value, "вес")


def parse_optional_float(value):
    if value in ("", None):
        return None
    return float(value)


def parse_user_input(payload: dict) -> UserInput:
    return UserInput(
        first_name=str(payload.get("first_name", payload.get("firstName", ""))).strip(),
        last_name=str(payload.get("last_name", payload.get("lastName", ""))).strip(),
        sex=normalize_sex(payload.get("sex", "мужчина")),
        current_weight=float(payload.get("current_weight", payload.get("weight", 0)) or 0),
        current_height=int(float(payload.get("current_height", payload.get("height", 0)) or 0)),
        current_age=int(float(payload.get("current_age", payload.get("age", 0)) or 0)),
        steps_per_day=int(float(payload.get("steps_per_day", payload.get("steps", 0)) or 0)),
        trainings_per_week=int(float(payload.get("trainings_per_week", payload.get("workouts", 0)) or 0)),
        training_minutes=int(float(payload.get("training_minutes", payload.get("minutesPerWorkout", 0)) or 0)),
        weekly_protein=float(payload.get("weekly_protein", payload.get("proteinWeek", 0)) or 0),
        weekly_fat=float(payload.get("weekly_fat", payload.get("fatWeek", 0)) or 0),
        weekly_carbs=float(payload.get("weekly_carbs", payload.get("carbsWeek", 0)) or 0),
        avg_kcal_per_day=float(payload.get("avg_kcal_per_day", payload.get("caloriesDay", 0)) or 0),
        goal_mode=normalize_goal_mode(payload.get("goal_mode", payload.get("goalType", "вес"))),
        goal_weight=parse_optional_float(payload.get("goal_weight", payload.get("targetWeight"))),
        current_body_fat=parse_optional_float(payload.get("current_body_fat", payload.get("currentFat"))),
        target_body_fat=parse_optional_float(payload.get("target_body_fat", payload.get("targetFat"))),
    )


@app.errorhandler(AppError)
def handle_app_error(error):
    return jsonify({"ok": False, "error": str(error)}), 400


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    payload = request.get_json(force=True, silent=False)
    data = parse_user_input(payload)
    result = calculator.calculate(data)

    if payload.get("auto_save_profile") and data.first_name.strip() and data.last_name.strip():
        saved_name = profile_storage.save_profile(data)
        result["saved_profile"] = saved_name

    if payload.get("auto_save_csv") or payload.get("autoSaveCsv"):
        history_storage.append_record(data)
        result["history_saved"] = True

    return jsonify({"ok": True, "result": result})


@app.route("/api/profiles", methods=["GET"])
def api_profiles():
    return jsonify({"ok": True, "profiles": profile_storage.list_profiles()})


@app.route("/api/profiles", methods=["POST"])
def api_save_profile():
    payload = request.get_json(force=True, silent=False)
    data = parse_user_input(payload)
    profile_name = profile_storage.save_profile(data)
    return jsonify({"ok": True, "profile_name": profile_name})


@app.route("/api/profiles/<path:profile_name>", methods=["GET"])
def api_get_profile(profile_name: str):
    profile = profile_storage.load_profile(profile_name)
    if profile is None:
        raise AppError("Профиль не найден.")
    return jsonify({"ok": True, "profile": asdict(profile)})


@app.route("/api/profiles/<path:profile_name>", methods=["DELETE"])
def api_delete_profile(profile_name: str):
    deleted = profile_storage.delete_profile(profile_name)
    if not deleted:
        raise AppError("Профиль не найден.")
    return jsonify({"ok": True, "deleted": True})


@app.route("/api/history.csv", methods=["GET"])
def api_history_csv():
    file_path = history_storage.download_file()
    return send_file(
        file_path,
        as_attachment=True,
        download_name="weight_history.csv",
        mimetype="text/csv",
    )


if __name__ == "__main__":
    app.run(debug=True)
