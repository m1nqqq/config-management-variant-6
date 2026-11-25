"""Проверки запуска переводчика отдельным процессом."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    """Запускает тот же интерпретатор и перехватывает оба потока в UTF-8."""
    return subprocess.run(
        [sys.executable, str(ROOT / "src" / "main.py"), *args],
        capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}, check=False,
    )


class CommandTests(unittest.TestCase):
    """Проверяет результат, диагностику и коды завершения."""

    def test_examples(self):
        """Оба предметных примера дают точные ожидаемые массивы."""
        cases = {
            "weather.cfg": [[-4, 2], [-1, 5]],
            "music.cfg": [[1, 1, 2], [1, 1, 2]],
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                result = run_cli("--input", ROOT / "examples" / name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(json.loads(result.stdout), expected)

    def test_file_errors(self):
        """Ошибки файла, кодировки и синтаксиса оставляют stdout пустым."""
        with TemporaryDirectory() as folder:
            path = Path(folder) / "файл с пробелами.cfg"
            for data in [None, b"\xff", b"[1;\n,]", b"${unknown}"]:
                with self.subTest(data=data):
                    if data is not None:
                        path.write_bytes(data)
                    result = run_cli("--input", path)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("Ошибка", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    if data == b"[1;\n,]":
                        self.assertIn("2:1", result.stderr)

    def test_input_required(self):
        """Пропуск ключа выводит подсказку argparse в stderr."""
        result = run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("--input", result.stderr)

    def test_large_integer(self):
        """Большое целое из файла UTF-8 с BOM выводится без потери цифр."""
        digits = "9" * 5000
        with TemporaryDirectory() as folder:
            path = Path(folder) / "big.cfg"
            path.write_text("+" + digits, encoding="utf-8-sig")
            result = run_cli("--input", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), digits)

    def test_deep_arrays(self):
        """Глубокий массив из ссылки целиком выводится в stdout."""
        nested = "[" * 2000 + "-1" + "]" * 2000
        with TemporaryDirectory() as folder:
            path = Path(folder) / "вложенный массив.cfg"
            path.write_text("global deep=" + nested + " ${deep}")
            result = run_cli("--input", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, nested + "\n")
        self.assertEqual(result.stderr, "")
