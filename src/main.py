"""Командная строка переводчика конфигураций в JSON."""

import argparse
import sys
from pathlib import Path

from converter import ConfigError, convert


def array_parts(values):
    """Чередует значения массива со знаками пунктуации JSON."""
    yield "["
    for index, value in enumerate(values):
        if index:
            yield ", "
        yield value
    yield "]"


def write_json(value, stream):
    """Выводит числа и массивы без рекурсивных вызовов."""
    pending = [iter((value,))]
    while pending:
        part = next(pending[-1], None)
        if part is None:
            pending.pop()
        elif isinstance(part, list):
            pending.append(array_parts(part))
        else:
            stream.write(str(part))
    stream.write("\n")


def main():
    """Читает указанный файл и выводит JSON либо сообщение об ошибке."""
    parser = argparse.ArgumentParser(description="Перевод конфигурации в JSON")
    parser.add_argument(
        "--input", required=True, type=Path, help="путь к файлу",
    )
    args = parser.parse_args()
    sys.set_int_max_str_digits(0)
    try:
        source = args.input.read_text(encoding="utf-8-sig")
        result = convert(source)
    except (OSError, UnicodeError, ConfigError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    write_json(result, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
