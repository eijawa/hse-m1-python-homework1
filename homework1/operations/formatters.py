from homework1.core.formatters import TableFormatter
from homework1.operations.operations import Operation


class OperationsTableFormatter(TableFormatter):
    def __init__(self, *, max_col_size: int = 28) -> None:
        """Форматтер для дата-класса Operation в виде таблицы"""
        super().__init__(class_=Operation, max_col_size=max_col_size)
