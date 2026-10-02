from collections.abc import Iterable, Sequence
from dataclasses import asdict, fields, is_dataclass
from datetime import date, datetime
from textwrap import shorten
from typing import Any


class TableFormatter:
    def __init__(
        self, class_: type, *, min_col_size: int = 6, max_col_size: int = 28
    ) -> None:
        """Форматтер для значений конкретного дата-класса в виде таблицы

        :param class_: Тип дата-класса
        :param min_col_size: Минимальный размер колонок. Должен быть больше или равен 6
        :param max_col_size: Максимальный размер колонок
        """
        assert is_dataclass(class_), "Передаваемое значение должно быть дата-классом"
        assert min_col_size >= 6, "Минимальная ширина колонки должна быть не меньше 6"

        self._class = class_

        self._col_size_space_indent = 2

        self._min_col_size = min_col_size
        self._max_col_size = max_col_size - self._col_size_space_indent

        self._row_vr_delim = "+"
        self._row_hr_delim = "-"
        self._col_vr_delim = "|"

        self._column_names: list[str] = [f.name for f in fields(class_)]
        self._column_types: list[str | Any] = [f.type for f in fields(class_)]
        self._column_sizes: list[int] = [0] * len(self._column_names)

    def _calc_columns(self, items: Iterable[dict]) -> None:
        """Не самая оптимальная функция подсчёта размера столбцов"""
        for item in items:
            for k, v in item.items():
                idx = self._column_names.index(k)

                size = max(len(str(v)), len(k)) if v else len(k)
                size += self._col_size_space_indent

                self._column_sizes[idx] = min(
                    max(size, self._column_sizes[idx], self._min_col_size),
                    self._max_col_size,
                )

    def _make_hr_line(self) -> str:
        """Метод генерации горизонтальной линии"""
        result = self._col_vr_delim

        for col_size in self._column_sizes:
            result += self._row_hr_delim * col_size + self._row_vr_delim

        return result

    def _make_header(self) -> str:
        """Метод генерации заголовка таблицы"""
        result = self._make_hr_line() + "\n"
        result += self._col_vr_delim

        for col_name, col_size in zip(
            self._column_names, self._column_sizes, strict=True
        ):
            col_name = shorten(col_name, col_size)
            result += f"{col_name:^{col_size}}" + self._col_vr_delim

        return result + "\n" + self._make_hr_line()

    def _make_row(self, item: dict) -> str:
        """Метод генерации строки таблицы"""
        result = self._col_vr_delim

        for k, v in item.items():
            idx = self._column_names.index(k)

            col_size = self._column_sizes[idx]
            col_type = self._column_types[idx]

            indent_ = "<"

            if isinstance(v, bool):
                indent_ = "^"
                v = str(v)

            if isinstance(v, int | float):
                indent_ = ">"

            # Я знаю, что здесь мог бы вызвать свой же кодек,
            # но по-хорошему для принтинга должен быть свой коде
            if isinstance(v, datetime):
                indent_ = ">"
                v = v.strftime("%Y-%m-%d %H:%M:%S")

            if isinstance(v, date):
                indent_ = ">"
                v = v.isoformat()

            if isinstance(v, str):
                v = shorten(v, col_size)

            if (isinstance(v, str) and not v) or v is None:
                v = ""

            result += f"{v:{indent_}{col_size}}" + self._col_vr_delim

        return result + "\n" + self._make_hr_line()

    def format(self, items: Sequence[Any]) -> str:
        """Форматирование списка значений в виде таблицы

        :param items: Список значений (все значения должны быть валидными дата-классами)
        :return: Строка-таблица
        """
        if not items:
            return ""

        # Да, это не самый точной способ определения, но fail-fast
        if not is_dataclass(items[0]):
            err = "Переданный список должен содержать дата-классы в качестве значений"
            raise ValueError(err)

        items = [asdict(i) for i in items]

        self._calc_columns(items)

        result = self._make_header() + "\n"

        for item in items:
            result += self._make_row(item) + "\n"

        return result
