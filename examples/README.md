# Примеры

Запуск из корня репозитория: `uv run python -m examples.<имя_модуля>`, например `uv run python -m examples.accounts_creation`.

- `accounts_creation.py` — создание расчётных и сберегательных счетов, ошибка валидации имени владельца, вывод карточек аккаунтов.
- `operations_history_table.py` — операции над счетами (депозит, снятие, проценты), включая неудачные, и вывод истории операций таблицей.
- `operations_load_dump.py` — загрузка истории операций из `data/transactions_dirty.csv` и `data/transactions_dirty.json` и сохранение в `dist/`.
- `accounts_restoration.py` — восстановление аккаунтов из истории операций в строгом и нестрогом режимах.
