"""Модуль с примерами загрузки и выгрузки истории операций"""

from pathlib import Path

from homework1.operations.formatters import OperationsTableFormatter
from homework1.operations.serialization import (
    OperationsHistoryCSVFSStorageHandler,
    OperationsHistoryJSONFSStorageHandler,
)

SRC_DIRPATH = Path(__file__).parent.parent
DATA_DIRPATH = SRC_DIRPATH / "data"
TRANSACTIONS_BASE_FILENAME = "transactions_dirty"

OUTPUT_DATA_DIRPATH = SRC_DIRPATH / "dist"

if __name__ == "__main__":
    if not OUTPUT_DATA_DIRPATH.exists():
        OUTPUT_DATA_DIRPATH.mkdir(exist_ok=True)

    _MAP = {
        ".csv": OperationsHistoryCSVFSStorageHandler,
        ".json": OperationsHistoryJSONFSStorageHandler,
    }

    _DUMPED_FILES_COUNTER = 0

    operations_formatter = OperationsTableFormatter()

    for suffix, handler_cls in _MAP.items():
        load_filepath = (DATA_DIRPATH / TRANSACTIONS_BASE_FILENAME).with_suffix(suffix)
        handler = handler_cls()

        history = handler.load(load_filepath)

        print(f"Файл по пути filepath={load_filepath} загружен")
        print(
            f"Вывод операций для типа: {suffix}. Эти операции прошли лишь базовую валидацию"
        )
        for *_, operations in history:
            print(operations_formatter.format(operations))

        dump_filepath = OUTPUT_DATA_DIRPATH / f"dump_{_DUMPED_FILES_COUNTER}{suffix}"
        handler.dump(dump_filepath, history)
        _DUMPED_FILES_COUNTER += 1

        print(f"Файл сохранён по пути filepath={dump_filepath}")

    print(f"Файлы сохранены в папке dirpath={OUTPUT_DATA_DIRPATH}. Файлы в папке:")
    print(*list(OUTPUT_DATA_DIRPATH.iterdir()), sep="\n")
