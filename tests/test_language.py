"""Проверки грамматики, вложенности и вычисления констант."""

import unittest

from src.converter import ConfigError, convert


class LanguageTests(unittest.TestCase):
    """Проверяет значения и ошибки одного документа."""

    def test_integers(self):
        """Знак и ведущие нули сохраняют числовое значение."""
        for source, expected in [("0", 0), ("-0", 0), ("+007", 7), ("-9", -9)]:
            with self.subTest(source=source):
                self.assertEqual(convert(source), expected)

    def test_arrays(self):
        """Пустые массивы, одиночные элементы и разные уровни вложенности."""
        self.assertEqual(convert("[]"), [])
        self.assertEqual(convert("[[1]; []; [2; [-3]]]"), [[1], [], [2, [-3]]])

    def test_constants(self):
        """Имена чувствительны к регистру и допускают цифры после буквы."""
        source = "global _x2=3 global X=[${_x2};[]] global x=${X} [${x};${X}]"
        self.assertEqual(convert(source), [[3, []], [3, []]])

    def test_comments(self):
        """Каждый вид комментария скрывает разметку другого вида."""
        source = "REM #= [\n global a #= REM\n ] =# = [2 REM ]\n] ${a} REM"
        self.assertEqual(convert(source), [2])
        self.assertEqual(convert("[#= one =#1;#= two =#2]"), [1, 2])

    def test_keyword_prefixes(self):
        """Префикс служебного слова может быть частью имени."""
        source = "global REM2=1 global globally=${REM2} ${globally}"
        self.assertEqual(convert(source), 1)

    def test_comment_or_name(self):
        """REM перед разделителем имени обозначает константу."""
        source = (
            "global REM } описание\n REM #= имя =# = 4\n"
            "global REMREM=${REM} [${REM REM пояснение\n};${REMREM}]"
        )
        self.assertEqual(convert(source), [4, 4])
        with self.assertRaises(ConfigError):
            convert("1REM слитно")

    def test_large_integer(self):
        """Число из 5000 цифр разбирается также при вызове без CLI."""
        self.assertEqual(convert("9" * 5000), 10**5000 - 1)

    def test_error_positions(self):
        """Позиция указывает на ошибочный токен или на конец файла."""
        cases = [("[1;\n", "2:1"), ("#=\n=#\n${x}", "3:3"), ("", "1:1")]
        for source, position in cases:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ConfigError, "^" + position + ":"):
                    convert(source)

    def test_syntax_errors(self):
        """Неполные конструкции и посторонние разделители отклоняются."""
        invalid = [
            "", "REM только комментарий", "global n=1", "1 2", "+", "--1",
            "1.2", "a", '"x"', "[1,2]", "[;1]", "[1;]", "[1 2]", "[[1]",
            "global 1a=1 0", "global я=1 0", "globala=1 0", "global x 1 0",
            "${}", "${a", "$ {a}", "[global a=1]", "#= без конца", "1 =#",
        ]
        for source in invalid:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ConfigError, "синтаксическая"):
                    convert(source)

    def test_invalid_references(self):
        """Ссылки требуют предшествующего объявления с тем же именем."""
        invalid = [
            "${x}", "global x=${x} 0", "global x=${y} global y=0 ${x}",
            "global x=2 [[${X}]]",
        ]
        for source in invalid:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ConfigError, "неизвестно"):
                    convert(source)

    def test_duplicate_name(self):
        """Повторное объявление того же имени является ошибкой."""
        with self.assertRaisesRegex(ConfigError, "повтор имени"):
            convert("global a=0 global a=1 ${a}")

    def test_document_scope(self):
        """Объявления одного документа недоступны в следующем."""
        self.assertEqual(convert("global a=1 ${a}"), 1)
        with self.assertRaises(ConfigError):
            convert("${a}")
