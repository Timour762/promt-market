# Локальный запуск

База проекта изолирована от установленной службы PostgreSQL: отдельный кластер .local/postgres, порт 5438, только 127.0.0.1. Пароль случайный, хранится в backend/.env; файлы .local и .env исключены из Git. Это окружение разработки, не production.

## После перезагрузки компьютера
Из корня проекта запустите базу, если она остановлена:

```powershell
& 'C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe' -D "$PWD\.local\postgres" status
& 'C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe' -D "$PWD\.local\postgres" -l "$PWD\.local\postgres.log" -w start
```

Backend в отдельном терминале:

```powershell
Set-Location backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8107
```

Frontend в другом терминале:

```powershell
Set-Location frontend
npm.cmd run dev
```

Каталог: http://localhost:3107/catalog
OpenAPI: http://127.0.0.1:8107/docs

## Миграции и начальные данные
Из backend:

```powershell
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m app.seed
```

Загрузка полных текстов дополнительно принимает `--content-file` с путём к исходному файлу владельца. Содержимое не печатается. Повторная загрузка не заменяет существующие товары и версии.

Таблицы: categories, prompts, prompt_versions. Полные тексты находятся только в prompt_versions, публичные endpoints читают метаданные опубликованных prompts. Защищённого endpoint выдачи текста ещё нет: он появится вместе с авторизацией и покупками.
Frontend получает данные серверными запросами к FastAPI через BACKEND_URL. Статический JSON backend остаётся только источником начальной загрузки, не источником ответов API.

Базу и .env нужно резервировать отдельно от Git. Сейчас настроено только локальное хранение, резервное копирование не автоматизировано.
