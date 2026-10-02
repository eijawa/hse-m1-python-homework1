from pathlib import Path

import pytest

from homework1.accounts.account_number_manager import AccountNumbersManager
from homework1.accounts.accounts import CheckingAccount, SavingsAccount
from homework1.accounts.restoration import AccountRestoreError, AccountRestoreManager
from homework1.core.exc import NegativeDepositError
from homework1.operations.serialization import OperationsHistoryCSVFSStorageHandler

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture
def history(make_operation):
    return [
        make_operation(name="deposit", value=100.0, balance_before=0.0, balance_after=100.0),
        make_operation(name="withdraw", value=30.0, balance_before=100.0, balance_after=70.0),
        make_operation(name="interest", value=5.0, balance_before=70.0, balance_after=73.5),
    ]


def _restore(account_type, operations, **kwargs):
    return AccountRestoreManager.restore(
        account_type=account_type,
        account_number_manager=kwargs.pop("account_number_manager", AccountNumbersManager()),
        operations=operations,
        **kwargs,
    )


# --- Выбор типа аккаунта ---


@pytest.mark.parametrize("account_type", ["other", "", None])
def test_unknown_account_type_raises(history, account_type):
    with pytest.raises(ValueError, match="невозможно восстановить"):
        _restore(account_type, history)


@pytest.mark.parametrize(
    ("account_type", "cls"), [("checking", CheckingAccount), ("savings", SavingsAccount)]
)
def test_restores_account_class(history, account_type, cls):
    account = _restore(account_type, history)

    assert type(account) is cls
    assert account.holder == "Unknown Account"


def test_account_number_passed(history):
    account = _restore("checking", history, account_number="ACC-100001")

    assert account.account_number == "ACC-100001"


def test_account_number_generated(history):
    assert _restore("checking", history).account_number == "ACC-0000"


# --- Восстановление истории и баланса ---


def test_checking_restore_skips_foreign_operations(history, capsys):
    account = _restore("checking", history)

    assert [op.name for op in account.get_history()] == ["deposit", "withdraw"]
    assert account.get_balance() == 70.0
    assert capsys.readouterr().out == ""


def test_savings_restore_applies_interest(history, capsys):
    account = _restore("savings", history)

    assert [op.name for op in account.get_history()] == ["deposit", "withdraw", "interest"]
    assert account.get_balance() == pytest.approx(73.5)
    assert capsys.readouterr().out == ""


def test_first_operation_sets_balance_and_kept_as_is(make_operation):
    first = make_operation(name="withdraw", value=1.0, balance_after=500.0)

    account = _restore("checking", [first])

    assert account.get_balance() == 500.0
    assert account.get_history() == [first]


def test_first_foreign_operation_dropped(make_operation):
    account = _restore(
        "checking",
        [
            make_operation(name="interest", balance_after=999.0),
            make_operation(name="deposit", value=10.0, balance_after=10.0),
        ],
    )

    assert account.get_balance() == 10.0
    assert [op.name for op in account.get_history()] == ["deposit"]


def test_balance_override_disabled_after_restore(history):
    account = _restore("checking", history)

    account.override_balance(1.0)

    assert account.get_balance() == 70.0


def test_replayed_failed_operation_matches_history(make_operation, capsys):
    account = _restore(
        "checking",
        [
            make_operation(name="deposit", balance_after=10.0),
            make_operation(name="withdraw", status="fail", value=100.0, balance_after=10.0),
        ],
    )

    assert [(op.name, op.status) for op in account.get_history()] == [
        ("deposit", "success"),
        ("withdraw", "fail"),
    ]
    assert account.get_balance() == 10.0
    assert capsys.readouterr().out == ""


def test_balance_mismatch_reported_and_restore_continues(make_operation, capsys):
    account = _restore(
        "checking",
        [
            make_operation(name="deposit", balance_after=10.0),
            make_operation(name="deposit", value=5.0, balance_after=999.0),
            make_operation(name="deposit", value=5.0, balance_after=20.0),
        ],
    )

    assert account.get_balance() == 20.0
    assert len(account.get_history()) == 3
    assert "(15.0 != 999.0)" in capsys.readouterr().out


# --- Ошибки создания аккаунта ---


def _assert_restore_error(exc_info, cause_type):
    assert isinstance(exc_info.value.__cause__, cause_type)


@pytest.mark.parametrize("strict", [True, False])
def test_empty_history_raises(strict):
    with pytest.raises(AccountRestoreError, match="ошибка при восстановлении аккаунта") as exc_info:
        _restore("checking", [], strict=strict)

    _assert_restore_error(exc_info, IndexError)


def test_only_foreign_operations_raises(make_operation):
    with pytest.raises(AccountRestoreError, match="ошибка при восстановлении аккаунта") as exc_info:
        _restore("checking", [make_operation(name="interest")])

    _assert_restore_error(exc_info, IndexError)


def test_invalid_first_balance_raises(make_operation):
    with pytest.raises(AccountRestoreError, match="валидным числом") as exc_info:
        _restore("checking", [make_operation(balance_after=None)])

    _assert_restore_error(exc_info, ValueError)


@pytest.mark.parametrize("strict", [True, False])
def test_occupied_account_number_raises(history, strict):
    manager = AccountNumbersManager()
    manager.addgen(1)

    with pytest.raises(AccountRestoreError, match="недоступен") as exc_info:
        _restore(
            "checking",
            history,
            account_number=1,
            account_number_manager=manager,
            strict=strict,
        )

    _assert_restore_error(exc_info, ValueError)


# --- Фатальные ошибки и strict ---


def _history_with_negative_deposit(make_operation):
    return [
        make_operation(name="deposit", balance_after=10.0),
        make_operation(name="deposit", value=-5.0, balance_after=10.0),
        make_operation(name="deposit", value=5.0, balance_after=15.0),
    ]


def test_fatal_error_raised_in_strict_mode(make_operation):
    with pytest.raises(AccountRestoreError, match="больше 0") as exc_info:
        _restore("checking", _history_with_negative_deposit(make_operation))

    assert isinstance(exc_info.value.__cause__, NegativeDepositError)


def test_fatal_error_skipped_in_non_strict_mode(make_operation, capsys):
    account = _restore(
        "checking", _history_with_negative_deposit(make_operation), strict=False
    )

    assert account.get_balance() == 15.0
    assert [op.value for op in account.get_history()] == [10.0, -5.0, 5.0]
    assert "strict=False" in capsys.readouterr().out


# --- clean_history ---


@pytest.mark.parametrize(
    ("fixture_name", "expected"),
    [("checking", ["deposit", "withdraw"]), ("savings", ["deposit", "withdraw", "interest"])],
)
def test_clean_history(request, history, fixture_name, expected):
    account = request.getfixturevalue(fixture_name)

    result = AccountRestoreManager.clean_history(account, history)

    assert [op.name for op in result] == expected


def test_clean_history_keeps_order_and_identity(checking, make_operation):
    ops = [make_operation(name=name) for name in ("withdraw", "transfer", "deposit")]

    assert AccountRestoreManager.clean_history(checking, ops) == [ops[0], ops[2]]


# --- Реальные данные ---


def test_restore_real_dirty_data_non_strict():
    manager = AccountNumbersManager()
    history = OperationsHistoryCSVFSStorageHandler().load(DATA_DIR / "transactions_dirty.csv")

    accounts = [
        _restore(
            account_type,
            operations,
            account_number=account_number,
            account_number_manager=manager,
            strict=False,
        )
        for account_number, account_type, operations in history
    ]

    assert [(a.account_number, a.account_type) for a in accounts] == [
        ("ACC-100001", "checking"),
        ("ACC-100002", "savings"),
        ("ACC-100003", "checking"),
        ("ACC-100004", "savings"),
    ]
    assert accounts[0].get_balance() == 5456.0
