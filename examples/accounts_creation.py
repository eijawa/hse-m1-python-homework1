"""Модуль с примерами создания аккаунтов"""

from homework1.accounts.account_number_manager import AccountNumbersManager
from homework1.accounts.accounts import CheckingAccount, SavingsAccount
from homework1.accounts.formatters import UniversalAccountFormatter

if __name__ == "__main__":
    ANM = AccountNumbersManager()

    accounts = []

    accounts.append(CheckingAccount("Barbara Hoppkins", account_number_manager=ANM))
    accounts.append(CheckingAccount("Мария Рожкова", account_number_manager=ANM))

    try:
        accounts.append(CheckingAccount("ПростоМария", account_number_manager=ANM))
    except Exception as e:
        err = f"Создание аккаунта завершилось с ошибкой: {e}"
        print(err)

    accounts.append(CheckingAccount("Ирина Авдеева", account_number_manager=ANM))

    accounts.append(SavingsAccount("Алина Бережливая", account_number_manager=ANM))

    for acc in accounts:
        print(UniversalAccountFormatter.format(acc))
