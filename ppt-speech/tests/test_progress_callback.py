"""pipeline 进度回调注入测试。

验证 ``process_slides`` 的 ``on_progress`` 回调机制：
- 事件序列正确（VALIDATING → ... → COMPLETED）。
- 百分比单调非减，COMPLETED 时为 100。
- 无回调时保持原 ``print`` 输出（CLI 行为兼容）。
- 有回调时 ``print`` 静默（服务端安静）。
- 无备注页只发 READING_NOTES，不发 SYNTHESIZING。
"""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ppt_speech.config import PptSpeechConfig
from ppt_speech.pipeline import (
    STAGE_COMPLETED,
    STAGE_EMBEDDING,
    STAGE_READING_NOTES,
    STAGE_SAVING,
    STAGE_SYNTHESIZING,
    STAGE_VALIDATING,
    process_slides,
)


class TestProgressCallback(unittest.IsolatedAsyncioTestCase):
    """on_progress 回调测试。"""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        # 写入占位 input.pptx 以通过 config.validate() 的文件存在性校验
        (self.temp_dir / "input.pptx").write_bytes(b"fake pptx content")
        self.config = PptSpeechConfig(
            input_dir=self.temp_dir,
            output_dir=self.temp_dir,
            input_filename="input.pptx",
            output_filename="output.pptx",
            temp_audio_dir=self.temp_dir / "temp_audio",
            auto_advance=False,
        )

    def tearDown(self) -> None:
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("ppt_speech.core.pipeline.embed_audio_autoplay")
    @patch("ppt_speech.core.pipeline.text_to_mp3", new_callable=AsyncMock)
    @patch("ppt_speech.core.pipeline.read_notes_text")
    async def test_event_sequence_and_percent(
        self,
        mock_read_notes: MagicMock,
        mock_text_to_mp3: AsyncMock,
        mock_embed: MagicMock,
    ) -> None:
        """有回调时事件序列含关键阶段，百分比单调非减，COMPLETED=100。"""
        mock_read_notes.return_value = "测试备注"
        mock_text_to_mp3.return_value = True

        mock_prs = MagicMock()
        mock_prs.slides = [MagicMock(), MagicMock()]

        events: list[dict] = []
        await process_slides(mock_prs, self.config, on_progress=events.append)

        stages = [e["stage"] for e in events]
        # 起止阶段
        self.assertEqual(stages[0], STAGE_VALIDATING)
        self.assertEqual(stages[-1], STAGE_COMPLETED)
        # 关键阶段均出现
        for required in (
            STAGE_SYNTHESIZING,
            STAGE_EMBEDDING,
            STAGE_SAVING,
            STAGE_COMPLETED,
        ):
            self.assertIn(required, stages)

        # 百分比单调非减
        percents = [e["percent"] for e in events]
        for prev, cur in zip(percents, percents[1:]):
            self.assertGreaterEqual(cur, prev)
        # COMPLETED 时 100
        self.assertEqual(percents[-1], 100.0)
        # 事件含 total_slides
        self.assertTrue(all(e["total_slides"] == 2 for e in events))

    @patch("ppt_speech.core.pipeline.embed_audio_autoplay")
    @patch("ppt_speech.core.pipeline.text_to_mp3", new_callable=AsyncMock)
    @patch("ppt_speech.core.pipeline.read_notes_text")
    async def test_no_notes_emits_only_reading(
        self,
        mock_read_notes: MagicMock,
        mock_text_to_mp3: AsyncMock,
        mock_embed: MagicMock,
    ) -> None:
        """无备注页只发 READING_NOTES，不发 SYNTHESIZING。"""
        mock_read_notes.return_value = ""
        mock_prs = MagicMock()
        mock_prs.slides = [MagicMock()]

        events: list[dict] = []
        await process_slides(mock_prs, self.config, on_progress=events.append)

        stages = [e["stage"] for e in events]
        self.assertIn(STAGE_READING_NOTES, stages)
        self.assertNotIn(STAGE_SYNTHESIZING, stages)
        self.assertNotIn(STAGE_EMBEDDING, stages)

    @patch("ppt_speech.core.pipeline.embed_audio_autoplay")
    @patch("ppt_speech.core.pipeline.text_to_mp3", new_callable=AsyncMock)
    @patch("ppt_speech.core.pipeline.read_notes_text")
    async def test_print_visible_without_callback(
        self,
        mock_read_notes: MagicMock,
        mock_text_to_mp3: AsyncMock,
        mock_embed: MagicMock,
    ) -> None:
        """无回调时原 print 文本输出到 stdout（CLI 兼容）。"""
        mock_read_notes.return_value = "测试备注"
        mock_text_to_mp3.return_value = True
        mock_prs = MagicMock()
        mock_prs.slides = [MagicMock()]

        buf = io.StringIO()
        with redirect_stdout(buf):
            await process_slides(mock_prs, self.config)

        output = buf.getvalue()
        self.assertIn("【第1页】生成语音", output)
        self.assertIn("✅ 处理完成", output)

    @patch("ppt_speech.core.pipeline.embed_audio_autoplay")
    @patch("ppt_speech.core.pipeline.text_to_mp3", new_callable=AsyncMock)
    @patch("ppt_speech.core.pipeline.read_notes_text")
    async def test_print_silent_with_callback(
        self,
        mock_read_notes: MagicMock,
        mock_text_to_mp3: AsyncMock,
        mock_embed: MagicMock,
    ) -> None:
        """有回调时原 print 静默（服务端安静）。"""
        mock_read_notes.return_value = "测试备注"
        mock_text_to_mp3.return_value = True
        mock_prs = MagicMock()
        mock_prs.slides = [MagicMock()]

        buf = io.StringIO()
        with redirect_stdout(buf):
            await process_slides(mock_prs, self.config, on_progress=lambda e: None)

        output = buf.getvalue()
        self.assertNotIn("生成语音", output)
        self.assertNotIn("处理完成", output)

    async def test_speak_ppt_notes_two_arg_call_preserved(self) -> None:
        """speak_ppt_notes 无回调时对 process_slides 精确 2 参调用（保 line 1013）。"""
        mock_prs = MagicMock()
        with (
            patch("ppt_speech.core.pipeline.Presentation", return_value=mock_prs),
            patch(
                "ppt_speech.core.pipeline.process_slides", new_callable=AsyncMock
            ) as mock_process,
        ):
            from ppt_speech.core.pipeline import speak_ppt_notes

            await speak_ppt_notes(self.config)
            # 精确 2 参调用（保住既有测试断言语义）
            mock_process.assert_called_once_with(mock_prs, self.config)


if __name__ == "__main__":
    unittest.main()
