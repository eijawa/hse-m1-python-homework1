import pytest

from homework1.accounts.account_number_manager import (
    AccountLimitReached,
    AccountNumbersManager,
)


def test_pattern(manager):
    assert manager.pattern == "ACC-{:04}"


def test_default_limit_allows_large_numbers():
    assert AccountNumbersManager().addgen(999_999) == "ACC-999999"


def test_generates_sequential_numbers(manager):
    assert [manager.addgen() for _ in range(3)] == ["ACC-0000", "ACC-0001", "ACC-0002"]


def test_manual_int_number(manager):
    assert manager.addgen(42) == "ACC-0042"


def test_manual_str_number(manager):
    assert manager.addgen("ACC-0042") == "ACC-0042"


def test_manual_str_number_without_padding(manager):
    assert manager.addgen("ACC-7") == "ACC-0007"


def test_duplicate_int_number_raises(manager):
    manager.addgen(5)

    with pytest.raises(ValueError, match="недоступен"):
        manager.addgen(5)


def test_duplicate_str_number_raises(manager):
    manager.addgen(5)

    with pytest.raises(ValueError, match="недоступен"):
        manager.addgen("ACC-0005")


def test_number_at_limit_raises(small_manager):
    with pytest.raises(ValueError, match="недоступен"):
        small_manager.addgen(3)


def test_invalid_str_number_raises(manager):
    with pytest.raises(ValueError):
        manager.addgen("ACC-abc")


def test_str_without_separator_raises(manager):
    with pytest.raises(IndexError):
        manager.addgen("ACC0001")


def test_generation_skips_occupied_numbers(manager):
    manager.addgen(0)
    manager.addgen(1)

    assert manager.addgen() == "ACC-0002"


def test_limit_reached(small_manager):
    for _ in range(3):
        small_manager.addgen()

    with pytest.raises(AccountLimitReached, match="лимит"):
        small_manager.addgen()


def test_limit_reached_is_value_error():
    assert issubclass(AccountLimitReached, ValueError)


def test_inc_does_not_advance_until_number_occupied(manager):
    assert manager._inc() == 0
    assert manager._inc() == 0


@pytest.mark.parametrize("number", [-1, "ACC--1"])
def test_negative_number_raises(manager, number):
    with pytest.raises(ValueError, match="отрицательным"):
        manager.addgen(number)


def test_negative_number_not_occupied(manager):
    with pytest.raises(ValueError):
        manager.addgen(-1)

    assert manager.addgen() == "ACC-0000"
