import csv
import json
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Generator, Sequence
from dataclasses import asdict, fields
from datetime import date, datetime
from os import PathLike
from pathlib import Path
from pprint import pformat
from typing import Any, NamedTuple

from .operations import Operation


class OperationCodec(ABC):
    """Кодек для сериализации операций"""

    @classmethod
    def encode(cls, value):
        """Простая функция дополнительного кодирования значений"""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")

        if isinstance(value, date):
            return value.isoformat()

        return value

    @classmethod
    def decode(cls, value, type: str | Any = None):
        """Простая функция дополнительного декодирования значений"""
        # Поскольку традиционно для сериализации-десериализации даты и времени
        # используют три подхода:
        # - перебор
        # - типы внутри
        # - типы в коде
        # То я решил воспользоваться последним вариантом, в связи с его простотой и тем,
        # что мои типы уже содержатся в аннотациях полей датакласса
        if type in (datetime, date):
            try:
                result = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                return result
            except:
                ...

            try:
                result = date.fromisoformat(value)
                return result
            except:
                raise

        # Обработка краевого кейса, тк уже два ночи и я не могу думать
        if value is None and type == float | None:
            return None

        if type in (float, float | None):
            return float(value)

        return value

    @classmethod
    def serialize(cls, value: Operation) -> dict:
        """Сериализация операции"""
        fields_ = {field_.name: field_ for field_ in fields(Operation)}

        kwargs = {}
        for k, v in asdict(value).items():
            nk = k

            if fields_[k].metadata:
                nk = fields_[k].metadata.get("serialization_alias", k)

                if not fields_[k].metadata.get("serialize_field", True):
                    nk = None

            if not nk:
                continue

            kwargs[nk] = cls.encode(v)

        return kwargs

    @classmethod
    def deserialize(cls, value: dict) -> Operation:
        """Десериализация операции"""
        kwargs = {}
        for k, v in value.items():
            nk = None
            for field_ in fields(Operation):
                if field_.name == k or (
                    field_.metadata
                    and field_.metadata.get("serialization_alias", None) == k
                ):
                    nk = field_.name
                    break

            if not nk:
                continue

            try:
                kwargs[nk] = cls.decode(v, type=field_.type)
            except ValueError as e:
                err = f"Произошла ошибка во время декодирования значения для поля {nk}={v}"
                raise ValueError(err) from e

        return Operation(**kwargs)


class AccountOperations(NamedTuple):
    """Дополнительный тип для более удобного представления операций,
    относящихся к конкретному аккаунту
    """

    account_number: str
    account_type: str
    operations: Sequence[Operation]


class OperationsHistoryFSStorageHandler(ABC):
    def __init__(self, codec: type[OperationCodec] = OperationCodec) -> None:
        """Базовый класс для сохранения или загрузки историй операций из файлов на файловой системе

        :param codec: Кодек для сериализации-десериализации значений
        """
        self.__codec = codec

    @property
    def codec(self) -> type[OperationCodec]:
        """Кодек для сериализации-десериализации значений"""
        return self.__codec

    @abstractmethod
    def _load(self, filepath: str | PathLike | Path) -> list[dict]:
        """Базовый метод загрузки данных по пути. Должен быть переопределён"""
        raise NotImplementedError

    @abstractmethod
    def _dump(self, filepath: str | PathLike | Path, history: list[dict]) -> None:
        """Базовый метод сохранения данных по пути. Должен быть переопределён"""
        raise NotImplementedError

    def _clean_history(
        self,
        history: Sequence[dict],
        *,
        account_type: str,
        allowed_operations: set[str],
    ) -> Generator[dict]:
        raise NotImplementedError(
            "Этот метод больше не нужен из-за избыточности, поскольку согласование теперь идёт на более высоком уровне"
        )

    def load(
        self,
        filepath: str | PathLike | Path,
    ) -> list[AccountOperations]:
        """Метод загрузки операций по аккаунтам из файла

        :param filepath: Путь к файлу с операциями
        :return: Список из операций, разделённых по конкретным аккаунтам
        """
        result = defaultdict(list)

        for raw_op in self._load(filepath=filepath):
            key = (raw_op.get("account_number"), raw_op.get("account_type"))

            try:
                result[key].append(self.codec.deserialize(raw_op))
            except Exception:
                print(f"Операцию не удалось распознать:\n{pformat(raw_op)}")

        return [AccountOperations(*k, v) for k, v in result.items()]

    def dump(
        self,
        filepath: str | PathLike | Path,
        history: list[AccountOperations],
    ) -> None:
        """Метод сохранения операций по аккаунтам в файл

        :param filepath: Путь к итоговому файлу
        :param history: Список из операций, относящихся к конкретному аккаунту
        """
        data = []

        for account_number, account_type, operations in history:
            for op in operations:
                data.append(
                    {
                        "account_number": account_number,
                        "account_type": account_type,
                        **self.codec.serialize(op),
                    }
                )

        self._dump(filepath, data)


class OperationsHistoryJSONFSStorageHandler(OperationsHistoryFSStorageHandler):
    """Сохранение и загрузка истории операций из JSON-файла"""

    def _load(self, filepath: str | PathLike | Path) -> list[dict]:
        with Path(filepath).open(mode="rb") as fp:
            return json.load(fp)

    def _dump(self, filepath: str | PathLike | Path, history: list[dict]) -> None:
        with Path(filepath).open(mode="w+") as fp:
            json.dump(history, fp)


class OperationsHistoryCSVFSStorageHandler(OperationsHistoryFSStorageHandler):
    """Сохранение и загрузка истории операций из CSV-файла"""

    def _load(self, filepath: str | PathLike | Path) -> list[dict]:
        with Path(filepath).open(mode="r", newline="") as fp:
            reader = csv.DictReader(fp)
            return list(reader)

    def _dump(self, filepath: str | PathLike | Path, history: list[dict]) -> None:
        assert history, "История операций должна быть передана для записи в файл"

        with Path(filepath).open(mode="w+") as fp:
            writer = csv.DictWriter(fp, fieldnames=history[0].keys())

            writer.writeheader()
            writer.writerows(history)
