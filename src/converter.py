"""Разбор конфигурации варианта №6 и подстановка значений констант."""

from decimal import Decimal
from pathlib import Path

from lark import Lark, UnexpectedInput, UnexpectedToken
from lark.exceptions import VisitError
from lark.visitors import Transformer_NonRecursive

GRAMMAR = Path(__file__).with_name("grammar.lark")
PARSER = Lark.open(
    str(GRAMMAR), parser="lalr", maybe_placeholders=False,
)


class ConfigError(ValueError):
    """Ошибка в тексте конфигурации."""


class Values(Transformer_NonRecursive):
    """Вычисляет значения в порядке их появления в дереве разбора."""

    def __init__(self):
        """Начинает обработку документа с пустой таблицей констант."""
        super().__init__()
        self.constants = {}

    def integer(self, children):
        """Преобразует знаковый литерал в целое число."""
        return int(Decimal(children[0]))

    def array(self, children):
        """Собирает уже вычисленные элементы массива."""
        return list(children)

    def rem_name(self, children):
        """Выделяет имя REM из токена с разделителем, сохраняя позицию."""
        return children[0].update(type="NAME", value="REM")

    def declaration(self, children):
        """Сохраняет значение константы после вычисления правой части."""
        name, value = children
        if name in self.constants:
            raise ConfigError(f"{name.line}:{name.column}: повтор имени {name}")
        self.constants[name] = value

    def reference(self, children):
        """Подставляет значение ранее объявленной константы."""
        name = children[0]
        if name not in self.constants:
            raise ConfigError(f"{name.line}:{name.column}: неизвестно {name}")
        return self.constants[name]

    def start(self, children):
        """Возвращает значение после объявлений."""
        return children[-1]


def convert(source):
    """Разбирает один документ и возвращает число или список для JSON."""
    try:
        tree = PARSER.parse(source)
    except UnexpectedInput as error:
        if isinstance(error, UnexpectedToken) and error.token.type == "$END":
            line = source.count("\n") + 1
            column = len(source.rsplit("\n", 1)[-1]) + 1
        else:
            line, column = error.line, error.column
        position = f"{line}:{column}"
        raise ConfigError(f"{position}: синтаксическая ошибка") from error
    try:
        return Values().transform(tree)
    except VisitError as error:
        if isinstance(error.orig_exc, ConfigError):
            raise error.orig_exc from error
        raise
