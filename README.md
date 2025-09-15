# SGR Prompt Lab — Minimal

Минимальная лаборатория для отладки промптов.

## Возможности
- Список моделей из Ollama (.env → OLLAMA_BASE_URL)
- Настройка temperature, top_p, max_tokens
- Три окна промптов (System, User, Context)
- Вопрос пользователя и контекст JSON
- Запрос обычный и stream
- Ответ + RAW ответ
- Логирование каждого запроса в `data/logs/*.json`

## Запуск
```
pip install fastapi uvicorn openai pydantic python-dotenv requests
cp .env.example .env
uvicorn app.server.main:app --host 0.0.0.0 --port 8000 --reload
```
