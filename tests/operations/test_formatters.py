from datetime import UTC, datetime

from homework1.operations.formatters import OperationsTableFormatter


def test_operation_columns():
    assert OperationsTableFormatter()._column_names == [
        "name",
        "status",
        "value",
        "balance_before",
        "balance_after",
        "created_at",
    ]


def test_format_operations(make_operation):
    op = make_operation(
        value=10.0,
        balance_before=None,
        balance_after=10.0,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )

    assert OperationsTableFormatter().format([op]) == (
        "|---------+---------+-------+----------------+---------------+--------------------------+\n"
        "|  name   | status  | value | balance_before | balance_after |        created_at        |\n"
        "|---------+---------+-------+----------------+---------------+--------------------------+\n"
        "|deposit  |success  |   10.0|                |           10.0|       2025-01-01 00:00:00|\n"
        "|---------+---------+-------+----------------+---------------+--------------------------+\n"
    )


def test_format_account_history(checking):
    checking.deposit(10.0)
    checking.withdraw(1000.0)

    lines = OperationsTableFormatter().format(checking.get_history()).splitlines()

    assert len(lines) == 7
    assert lines[3].startswith("|deposit")
    assert "|success" in lines[3]
    assert lines[5].startswith("|withdraw")
    assert "|fail" in lines[5]


def test_custom_max_col_size(make_operation):
    formatter = OperationsTableFormatter(max_col_size=10)

    assert formatter._max_col_size == 8
    assert "balance_before" not in formatter.format([make_operation()])
