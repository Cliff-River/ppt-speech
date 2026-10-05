"""CLI 子命令单元测试。

覆盖顶层解析器结构、向后兼容注入、create/voice 子命令参数、
音色过滤与表格渲染，使用 Python 标准 unittest 框架。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ppt_speech.cli.main import _ensure_subcommand, _normalize_argv, build_parser
from ppt_speech.cli.voices import filter_voices, format_voices_table, load_voices


def _parse(argv: list[str]):
    """按顶层入口相同规则解析参数，返回 Namespace。"""
    argv = _normalize_argv(_ensure_subcommand(argv))
    return build_parser().parse_args(argv)


class NormalizeArgvTest(unittest.TestCase):
    """`--rate "-10%"` 等号化改写测试。"""

    def test_space_separated_negative_rate(self):
        self.assertEqual(
            _normalize_argv(["-r", "-10%"]),
            ["-r=-10%"],
        )

    def test_plain_tokens_unchanged(self):
        # `-r` 后跟值总是被等号化改写（既有行为，含正数语速）。
        self.assertEqual(
            _normalize_argv(["create", "-i", "a.pptx", "-r", "+5%"]),
            ["create", "-i", "a.pptx", "-r=+5%"],
        )


class EnsureSubcommandTest(unittest.TestCase):
    """向后兼容的子命令注入测试。"""

    def test_explicit_subcommand_kept(self):
        self.assertEqual(_ensure_subcommand(["voice", "-l", "zh"]), ["voice", "-l", "zh"])

    def test_legacy_flags_inject_create(self):
        self.assertEqual(
            _ensure_subcommand(["-i", "a.pptx"]),
            ["create", "-i", "a.pptx"],
        )

    def test_top_help_not_injected(self):
        self.assertEqual(_ensure_subcommand(["--help"]), ["--help"])
        self.assertEqual(_ensure_subcommand(["-h"]), ["-h"])

    def test_empty_argv(self):
        self.assertEqual(_ensure_subcommand([]), [])


class CreateSubcommandTest(unittest.TestCase):
    """create 子命令参数解析与默认值测试。"""

    def test_defaults_preserved(self):
        args = _parse(["create"])
        self.assertEqual(args.input, "data/input.pptx")
        self.assertEqual(args.output, "data/output.pptx")
        self.assertEqual(args.voice, "zh-CN-XiaoxiaoNeural")
        self.assertEqual(args.rate, "+0%")
        self.assertTrue(args.auto_advance)
        self.assertTrue(callable(args.handler))

    def test_legacy_flat_invocation_maps_to_create(self):
        args = _parse(["-i", "a.pptx", "-o", "b.pptx", "-v", "en-US-AriaNeural"])
        self.assertEqual(args.command, "create")
        self.assertEqual(args.input, "a.pptx")
        self.assertEqual(args.output, "b.pptx")
        self.assertEqual(args.voice, "en-US-AriaNeural")

    def test_no_auto_advance(self):
        args = _parse(["create", "--no-auto-advance"])
        self.assertFalse(args.auto_advance)

    def test_negative_rate_via_space(self):
        args = _parse(["create", "-r", "-10%"])
        self.assertEqual(args.rate, "-10%")

    def test_run_raises_on_missing_input(self):
        args = _parse(["create", "-i", "definitely/missing.pptx"])
        with self.assertRaises(FileNotFoundError):
            args.handler(args)


class VoiceSubcommandTest(unittest.TestCase):
    """voice 子命令参数解析测试。"""

    def test_defaults(self):
        args = _parse(["voice"])
        self.assertIsNone(args.keyword)
        self.assertIsNone(args.locale)
        self.assertIsNone(args.gender)
        self.assertIsNone(args.voice_type)
        self.assertFalse(args.cache)
        self.assertFalse(args.refresh)
        self.assertFalse(args.json)

    def test_filters_parsed(self):
        args = _parse(["voice", "xiaoxiao", "-l", "zh-CN", "-g", "FEMALE", "-t", "News"])
        self.assertEqual(args.keyword, "xiaoxiao")
        self.assertEqual(args.locale, "zh-CN")
        self.assertEqual(args.gender, "female")  # 统一转为小写
        self.assertEqual(args.voice_type, "News")

    def test_cache_refresh_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            _parse(["voice", "--cache", "--refresh"])


class FilterVoicesTest(unittest.TestCase):
    """音色多条件组合过滤测试。"""

    VOICES = [
        {
            "ShortName": "zh-CN-XiaoxiaoNeural",
            "Gender": "Female",
            "Locale": "zh-CN",
            "FriendlyName": "Microsoft Xiaoxiao Online (Natural) - Chinese (Mainland)",
            "VoiceTag": {"ContentCategories": ["News"], "VoicePersonalities": ["Warm"]},
        },
        {
            "ShortName": "en-US-AriaNeural",
            "Gender": "Female",
            "Locale": "en-US",
            "FriendlyName": "Microsoft Aria Online (Natural) - English (United States)",
            "VoiceTag": {"ContentCategories": ["Novel"], "VoicePersonalities": ["Sincere"]},
        },
        {
            "ShortName": "en-US-GuyNeural",
            "Gender": "Male",
            "Locale": "en-US",
            "FriendlyName": "Microsoft Guy Online (Natural) - English (United States)",
            "VoiceTag": {"ContentCategories": [], "VoicePersonalities": []},
        },
    ]

    def test_no_filter_returns_all(self):
        self.assertEqual(len(filter_voices(self.VOICES)), 3)

    def test_keyword_search(self):
        result = filter_voices(self.VOICES, keyword="xiaoxiao")
        self.assertEqual([v["ShortName"] for v in result], ["zh-CN-XiaoxiaoNeural"])

    def test_locale_prefix_match(self):
        result = filter_voices(self.VOICES, locale="zh")
        self.assertEqual([v["Locale"] for v in result], ["zh-CN"])

    def test_gender_filter_case_insensitive(self):
        result = filter_voices(self.VOICES, gender="FEMALE")
        self.assertEqual(len(result), 2)

    def test_combined_filters(self):
        result = filter_voices(self.VOICES, locale="en-US", gender="female", voice_type="sincere")
        self.assertEqual([v["ShortName"] for v in result], ["en-US-AriaNeural"])

    def test_no_match(self):
        self.assertEqual(filter_voices(self.VOICES, keyword="不存在"), [])


class VoicesIoTest(unittest.TestCase):
    """音色缓存读取与表格渲染测试。"""

    def test_load_voices(self):
        voices = [{"ShortName": "zh-CN-XiaoxiaoNeural"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voices.json"
            path.write_text(json.dumps(voices, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(load_voices(str(path)), voices)

    def test_load_voices_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_voices("definitely/missing/voices.json")

    def test_format_table_contains_columns(self):
        table = format_voices_table(self.VOICES if hasattr(self, "VOICES") else [])
        self.assertIn("ShortName", table)

    def test_format_table_rows(self):
        voices = FilterVoicesTest.VOICES
        table = format_voices_table(voices)
        for name in (v["ShortName"] for v in voices):
            self.assertIn(name, table)


class TopLevelParserTest(unittest.TestCase):
    """顶层解析器结构测试。"""

    def test_unknown_flag_not_silently_accepted(self):
        with self.assertRaises(SystemExit):
            _parse(["create", "--not-exist"])

    def test_bare_invocation_has_no_handler(self):
        args = build_parser().parse_args([])
        self.assertIsNone(getattr(args, "handler", None))


if __name__ == "__main__":
    unittest.main()
