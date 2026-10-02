from dataclasses import dataclass
from datetime import date, datetime

import pytest

from homework1.core.formatters import TableFormatter


@dataclass
class Row:
    name: str
    amount: float
    day: date | None = None


def _lines(text: str) -> list[str]:
    return text.splitlines()


def test_requires_dataclass():
    with pytest.raises(AssertionError, match="дата-классом"):
        TableFormatter(dict)


def test_columns_from_dataclass_fields():
    formatter = TableFormatter(Row)

    assert formatter._column_names == ["name", "amount", "day"]
    assert formatter._column_types == [str, float, date | None]


def test_empty_items():
    assert TableFormatter(Row).format([]) == ""


def test_items_must_be_dataclasses():
    with pytest.raises(ValueError, match="дата-классы"):
        TableFormatter(Row).format([{"name": "a", "amount": 1.0}])


def test_single_row_layout():
    result = TableFormatter(Row).format([Row("ab", 1.5, date(2025, 1, 2))])

    assert result == (
        "|------+--------+------------+\n"
        "| name | amount |    day     |\n"
        "|------+--------+------------+\n"
        "|ab    |     1.5|  2025-01-02|\n"
        "|------+--------+------------+\n"
    )


def test_datetime_formatted():
    @dataclass
    class Event:
        at: datetime

    result = TableFormatter(Event).format([Event(datetime(2025, 1, 2, 3, 4, 5, 6))])

    assert "2025-01-02 03:04:05|" in result
    assert ".000006" not in result


def test_none_rendered_empty():
    [_, _, _, row, _] = _lines(TableFormatter(Row).format([Row("ab", 1.5)]))

    assert row == "|ab    |     1.5|      |"


def test_custom_min_col_size():
    @dataclass
    class Tiny:
        a: str

    [_, header, _, row, _] = _lines(TableFormatter(Tiny, min_col_size=8).format([Tiny("x")]))

    assert header == "|   a    |"
    assert row == "|x       |"


def test_long_string_shortened_to_max_col_size():
    formatter = TableFormatter(Row, max_col_size=12)

    [_, _, _, row, _] = _lines(formatter.format([Row("very long name here", 1.0)]))

    # 12 - 2 символа отступа = 10 на значение
    assert row.startswith("|very [...]|")


def test_every_row_followed_by_separator():
    result = TableFormatter(Row).format([Row("ab", 1.0), Row("cd", 2.0)])
    lines = _lines(result)

    assert len(lines) == 7
    assert lines[0] == lines[2] == lines[4] == lines[6]
    assert result.endswith("\n")


def test_column_fits_widest_value():
    result = TableFormatter(Row).format([Row("long name", 1.0), Row("ab", 2.0)])

    assert "|long name" in result


def test_narrow_last_row_does_not_break_long_value():
    @dataclass
    class Tiny:
        a: str

    TableFormatter(Tiny).format([Tiny("long value"), Tiny("x")])


def test_zero_rendered():
    [_, _, _, row, _] = _lines(TableFormatter(Row).format([Row("ab", 0.0)]))

    assert "0.0" in row


def test_empty_string_rendered_empty():
    [_, _, _, row, _] = _lines(TableFormatter(Row).format([Row("", 1.0)]))

    assert row.startswith("|      |")


def test_short_column_padded_to_default_min_size():
    @dataclass
    class Short:
        a: str

    [_, header, _, row, _] = _lines(TableFormatter(Short).format([Short("ab")]))

    assert header == "|  a   |"
    assert row == "|ab    |"


@pytest.mark.parametrize("size", [0, 4, 5])
def test_min_col_size_too_small(size):
    with pytest.raises(AssertionError, match="не меньше 6"):
        TableFormatter(Row, min_col_size=size)


@pytest.mark.parametrize("value", [True, False])
def test_bool_rendered_as_text(value):
    @dataclass
    class Flag:
        enabled: bool

    [_, _, _, row, _] = _lines(TableFormatter(Flag).format([Flag(value)]))

    assert row == f"|{value!s:^9}|"
