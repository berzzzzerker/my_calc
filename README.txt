Запуск:
1. Открой папку проекта в терминале.
2. Установи Flask:
   pip install -r requirements.txt
3. Запусти сервер:
   python app.py
4. Открой в браузере:
   http://127.0.0.1:5000

Структура:
- app.py                -> Python backend с логикой и API
- templates/index.html  -> HTML/CSS/JS интерфейс
- profiles.json         -> профили
- weight_history.csv    -> история расчётов


Деплой на Render:
- Рекомендуемый Start Command: gunicorn wsgi:app
- Если деплой падал с ImportError про circular import, проверь что файл calculator.py содержит расчётную логику, а не импорт самого себя.
