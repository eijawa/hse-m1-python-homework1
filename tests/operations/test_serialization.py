import csv
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from homework1.operations.operations import Operation
from homework1.operations.serialization import (
    AccountOperations,
    OperationCodec,
    OperationsHistoryCSVFSStorageHandler,
    OperationsHistoryFSStorageHandler,
    OperationsHistoryJSONFSStorageHandler,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _raw(**overrides) -> dict:
    return {
        "account_number": "ACC-0001",
        "account_type": "checking",
        "date": "2025-09-27 22:17:26",
        "operation": "deposit",
        "amount": 100.0,
        "balance_after": 200.0,
        "status": "success",
    } | overrides


# --- OperationCodec.encode ---


def test_encode_datetime():
    assert OperationCodec.encode(datetime(2025, 9, 27, 22, 17, 26, 123, tzinfo=UTC)) == "2025-09-27 22:17:26"


def test_encode_date():
    assert OperationCodec.encode(date(2025, 9, 27)) == "2025-09-27"


@pytest.mark.parametrize("value", [1, 1.5, "text", None, 1.1])
def test_encode_passthrough(value):
    assert OperationCodec.encode(value) == value


# --- OperationCodec.decode ---


@pytest.mark.parametrize("type_", [datetime, date])
def test_decode_datetime_string(type_):
    assert OperationCodec.decode("2025-09-27 22:17:26", type=type_) == datetime(2025, 9, 27, 22, 17, 26)


def test_decode_iso_date():
    assert OperationCodec.decode("2025-09-27", type=datetime) == date(2025, 9, 27)


@pytest.mark.parametrize("value", ["28/09/2025 22:17", "2025-17-34 12:00:00", "garbage"])
def test_decode_invalid_date(value):
    with pytest.raises(ValueError):
        OperationCodec.decode(value, type=datetime)


def test_decode_non_string_date_raises_type_error():
    with pytest.raises(TypeError):
        OperationCodec.decode(123, type=datetime)


@pytest.mark.parametrize("type_", [None, str, "datetime"])
def test_decode_passthrough(type_):
    assert OperationCodec.decode("2025-09-27", type=type_) == "2025-09-27"


@pytest.mark.parametrize("type_", [float, float | None])
@pytest.mark.parametrize(("value", "expected"), [("1.5", 1.5), ("-0.5", -0.5), ("5", 5.0), ("1e3", 1000.0), (2, 2.0)])
def test_decode_float_field(type_, value, expected):
    result = OperationCodec.decode(value, type=type_)

    assert result == expected
    assert isinstance(result, float)


@pytest.mark.parametrize("value", ["", "abc"])
def test_decode_float_field_invalid_str(value):
    with pytest.raises(ValueError):
        OperationCodec.decode(value, type=float)


def test_decode_optional_float_field_none():
    assert OperationCodec.decode(None, type=float | None) is None


def test_decode_required_float_field_none():
    with pytest.raises(TypeError):
        OperationCodec.decode(None, type=float)


def test_decode_str_without_type_passthrough():
    assert OperationCodec.decode("1.5") == "1.5"


# --- OperationCodec.serialize / deserialize ---


def test_serialize_uses_aliases(make_operation):
    op = make_operation(
        value=10.0,
        balance_before=5.0,
        balance_after=15.0,
        created_at=datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC),
    )

    assert OperationCodec.serialize(op) == {
        "operation": "deposit",
        "status": "success",
        "amount": 10.0,
        "balance_after": 15.0,
        "date": "2025-01-02 03:04:05",
    }


def test_deserialize_aliases():
    op = OperationCodec.deserialize(_raw())

    assert op == Operation(
        name="deposit",
        status="success",
        value=100.0,
        balance_after=200.0,
        created_at=datetime(2025, 9, 27, 22, 17, 26),
    )
    assert op.balance_before == 0.0


def test_deserialize_field_names():
    op = OperationCodec.deserialize(
        {
            "name": "withdraw",
            "status": "fail",
            "value": 1,
            "balance_before": 5,
            "created_at": "2025-01-01",
        }
    )

    assert op.name == "withdraw"
    assert op.balance_before == 5
    assert op.created_at == date(2025, 1, 1)


def test_deserialize_ignores_unknown_keys():
    op = OperationCodec.deserialize(_raw(extra="x"))

    assert not hasattr(op, "extra")
    assert not hasattr(op, "account_number")


def test_deserialize_missing_date_uses_default():
    raw = _raw()
    del raw["date"]

    assert OperationCodec.deserialize(raw).created_at.tzinfo is UTC


def test_deserialize_invalid_date():
    with pytest.raises(ValueError, match="created_at=28/09/2025") as exc_info:
        OperationCodec.deserialize(_raw(date="28/09/2025"))

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_deserialize_text_fields_not_converted():
    op = OperationCodec.deserialize(_raw(status="1.5", operation="2.0"))

    assert (op.status, op.name) == ("1.5", "2.0")


def test_deserialize_invalid_amount():
    with pytest.raises(ValueError, match="value=abc"):
        OperationCodec.deserialize(_raw(amount="abc"))


def test_deserialize_csv_like_row():
    op = OperationCodec.deserialize(_raw(amount="921.0", balance_after="2121.0"))

    assert (op.value, op.balance_after) == (921.0, 2121.0)


def test_deserialize_csv_empty_amount():
    with pytest.raises(ValueError, match="value="):
        OperationCodec.deserialize(_raw(amount=""))


def test_deserialize_null_amount():
    # TypeError не оборачивается, в load такая строка пропускается
    with pytest.raises(TypeError):
        OperationCodec.deserialize(_raw(amount=None))


def test_deserialize_null_balance_after():
    assert OperationCodec.deserialize(_raw(balance_after=None)).balance_after is None


def test_deserialize_missing_required_field():
    raw = _raw()
    del raw["operation"]

    with pytest.raises(TypeError):
        OperationCodec.deserialize(raw)


def test_serialize_deserialize_round_trip(make_operation):
    op = make_operation(created_at=datetime(2025, 1, 2, 3, 4, 5))

    restored = OperationCodec.deserialize(OperationCodec.serialize(op))

    assert restored.name == op.name
    assert restored.value == op.value
    assert restored.balance_after == op.balance_after
    assert restored.created_at == op.created_at


# --- Базовый обработчик ---


def test_base_handler_is_abstract():
    with pytest.raises(TypeError):
        OperationsHistoryFSStorageHandler()


def test_base_abstract_methods_raise(tmp_path):
    class Handler(OperationsHistoryFSStorageHandler):
        def _load(self, filepath):
            return super()._load(filepath)

        def _dump(self, filepath, history):
            return super()._dump(filepath, history)

    handler = Handler()

    with pytest.raises(NotImplementedError):
        handler._load(tmp_path)
    with pytest.raises(NotImplementedError):
        handler._dump(tmp_path, [])


def test_clean_history_is_removed():
    with pytest.raises(NotImplementedError, match="больше не нужен"):
        OperationsHistoryJSONFSStorageHandler()._clean_history(
            [], account_type="checking", allowed_operations=set()
        )


def test_default_codec():
    assert OperationsHistoryJSONFSStorageHandler().codec is OperationCodec


def test_custom_codec_used(tmp_path):
    class UpperCodec(OperationCodec):
        @classmethod
        def serialize(cls, value):
            return {"operation": value.name.upper()}

    path = tmp_path / "out.json"
    OperationsHistoryJSONFSStorageHandler(codec=UpperCodec).dump(
        path, [AccountOperations("ACC-1", "checking", [Operation("deposit", "success", 1)])]
    )

    assert json.loads(path.read_text()) == [
        {"account_number": "ACC-1", "account_type": "checking", "operation": "DEPOSIT"}
    ]


# --- JSON ---


def test_json_load_groups_by_account(tmp_path):
    path = tmp_path / "in.json"
    path.write_text(
        json.dumps(
            [
                _raw(),
                _raw(account_number="ACC-0002", account_type="savings"),
                _raw(operation="withdraw"),
            ]
        )
    )

    result = OperationsHistoryJSONFSStorageHandler().load(path)

    assert [(number, type_, [op.name for op in ops]) for number, type_, ops in result] == [
        ("ACC-0001", "checking", ["deposit", "withdraw"]),
        ("ACC-0002", "savings", ["deposit"]),
    ]
    assert all(isinstance(item, AccountOperations) for item in result)


def test_json_load_reports_bad_rows(tmp_path, capsys):
    path = tmp_path / "in.json"
    path.write_text(json.dumps([_raw(date="bad"), _raw()]))

    [(_, _, ops)] = OperationsHistoryJSONFSStorageHandler().load(str(path))

    assert len(ops) == 1
    assert "Операцию не удалось распознать" in capsys.readouterr().out


def test_json_load_missing_account_keys(tmp_path):
    path = tmp_path / "in.json"
    path.write_text(json.dumps([{"operation": "deposit", "status": "success", "amount": 1}]))

    [(number, type_, ops)] = OperationsHistoryJSONFSStorageHandler().load(path)

    assert (number, type_, len(ops)) == (None, None, 1)


def test_json_load_empty(tmp_path):
    path = tmp_path / "in.json"
    path.write_text("[]")

    assert OperationsHistoryJSONFSStorageHandler().load(path) == []


def test_json_load_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        OperationsHistoryJSONFSStorageHandler().load(tmp_path / "missing.json")


def test_json_dump_load_round_trip(tmp_path, make_operation):
    handler = OperationsHistoryJSONFSStorageHandler()
    path = tmp_path / "out.json"
    ops = [
        make_operation(value=10.0, balance_after=10.0, created_at=datetime(2025, 1, 1, 12)),
        make_operation(name="withdraw", status="fail", value=5.0, balance_after=10.0),
    ]

    handler.dump(path, [AccountOperations("ACC-0001", "checking", ops)])
    [(number, type_, restored)] = handler.load(path)

    assert (number, type_) == ("ACC-0001", "checking")
    assert [(op.name, op.status, op.value, op.balance_after) for op in restored] == [
        ("deposit", "success", 10.0, 10.0),
        ("withdraw", "fail", 5.0, 10.0),
    ]
    assert restored[0].created_at == datetime(2025, 1, 1, 12)


def test_json_dump_writes_flat_records(tmp_path, make_operation):
    path = tmp_path / "out.json"
    op = make_operation(value=1.0, balance_after=2.0, created_at=datetime(2025, 1, 1))

    OperationsHistoryJSONFSStorageHandler().dump(
        path,
        [
            AccountOperations("ACC-1", "checking", [op]),
            AccountOperations("ACC-2", "savings", []),
        ],
    )

    assert json.loads(path.read_text()) == [
        {
            "account_number": "ACC-1",
            "account_type": "checking",
            "operation": "deposit",
            "status": "success",
            "amount": 1.0,
            "balance_after": 2.0,
            "date": "2025-01-01 00:00:00",
        }
    ]


def test_json_load_real_dirty_data(capsys):
    result = OperationsHistoryJSONFSStorageHandler().load(DATA_DIR / "transactions_dirty.json")

    assert [(number, type_, len(ops)) for number, type_, ops in result] == [
        ("ACC-100001", "checking", 21),
        ("ACC-100002", "savings", 22),
        ("ACC-100003", "checking", 20),
        ("ACC-100004", "savings", 26),
    ]
    # 13 строк с плохой датой и 3 с пустым amount
    assert capsys.readouterr().out.count("Операцию не удалось распознать") == 16


# --- CSV ---


def test_csv_dump(tmp_path, make_operation):
    path = tmp_path / "out.csv"
    op = make_operation(value=1.0, balance_after=2.0, created_at=datetime(2025, 1, 1))

    OperationsHistoryCSVFSStorageHandler().dump(
        path, [AccountOperations("ACC-1", "checking", [op, op])]
    )

    with path.open(newline="") as fp:
        rows = list(csv.DictReader(fp))

    assert rows == [
        {
            "account_number": "ACC-1",
            "account_type": "checking",
            "operation": "deposit",
            "status": "success",
            "amount": "1.0",
            "balance_after": "2.0",
            "date": "2025-01-01 00:00:00",
        }
    ] * 2


def test_csv_dump_empty_history(tmp_path):
    with pytest.raises(AssertionError, match="История операций"):
        OperationsHistoryCSVFSStorageHandler().dump(tmp_path / "out.csv", [])


def test_csv_dump_load_round_trip(tmp_path, make_operation):
    handler = OperationsHistoryCSVFSStorageHandler()
    path = tmp_path / "out.csv"
    op = make_operation(value=1.0, balance_after=2.0, created_at=datetime(2025, 1, 1, 12))

    handler.dump(path, [AccountOperations("ACC-1", "checking", [op])])
    [loaded] = handler.load(path)

    assert isinstance(loaded, AccountOperations)
    assert (loaded.account_number, loaded.account_type) == ("ACC-1", "checking")
    [restored] = loaded.operations
    assert (restored.name, restored.status, restored.value, restored.balance_after) == (
        "deposit",
        "success",
        1.0,
        2.0,
    )
    assert restored.created_at == datetime(2025, 1, 1, 12)


def test_csv_load_real_dirty_data(capsys):
    result = OperationsHistoryCSVFSStorageHandler().load(DATA_DIR / "transactions_dirty.csv")

    assert [(item.account_number, item.account_type, len(item.operations)) for item in result] == [
        ("ACC-100001", "checking", 21),
        ("ACC-100002", "savings", 22),
        ("ACC-100003", "checking", 20),
        ("ACC-100004", "savings", 26),
    ]
    # 13 строк с плохой датой и 3 с пустым amount
    assert capsys.readouterr().out.count("Операцию не удалось распознать") == 16
