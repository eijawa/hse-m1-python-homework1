class AccountLimitReached(ValueError):
    """Ошибка, обозначающая, что превышен лимит доступных аккаунтов"""


class AccountNumbersManager:
    def __init__(self, *, limit: int = 1_000_000) -> None:
        """Менеджер номеров аккаунтов.

        Необходим для отслеживания созданных аккаунтов и корректной выдачи новых номеров.
        Важно понимать, что менеджер отслеживает дубликаты, чтобы не было двух одинаковых аккаунтов

        :param limit: Максимальный размер хранилища для номеров
        """
        self.__occupied_ids = set()
        self.__counter = 0

        self.__limit = limit

        self.__pattern = "ACC-{:04}"

    def __extract_number(self, value: str) -> int:
        """Получение номера аккаунта из строкового значения"""
        return int(value.split("-", maxsplit=1)[1])

    def _inc(self) -> int:
        """Получение следующего доступного номера.

        Метод является недетерминированным,
        т.е. его повторный вызов даст другое значение
        и будет иметь дальнейшие эффекты на работу всей системы

        :raises AccountLimitReached: Превышен лимит доступных аккаунтов
        """
        while self.__counter < self.__limit and self.__counter in self.__occupied_ids:
            self.__counter += 1

        if self.__counter >= self.__limit:
            err = "Превышен лимит доступных аккаунтов"
            raise AccountLimitReached(err)

        return self.__counter

    @property
    def pattern(self) -> str:
        """Строчный шаблон номера аккаунта"""
        return self.__pattern

    def addgen(self, number: int | str | None = None) -> str:
        """Добавление или генерация номера аккаунта.

        Если параметр передан, то будет совершена попытка присвоить этот номер,
        если это невозможно, то будет поднята ошибка.
        В случае, если параметр не передан, то номер будет сгенерирован автоматически

        :param number: Номер для ручной установки
        :return: Отформатированный номер аккаунта в строковом представлении

        :raise ValueError: Введённый вручную номер недоступен или некорректен
        """
        if number is None:
            number = self._inc()

        if isinstance(number, str):
            number = self.__extract_number(number)

        if number in self.__occupied_ids or number >= self.__limit:
            err = "Введённый вручную номер аккаунта недоступен"
            raise ValueError(err)

        if number < 0:
            err = "Итоговый номер не должен быть отрицательным"
            raise ValueError(err)

        self.__occupied_ids.add(number)

        return self.pattern.format(number)
