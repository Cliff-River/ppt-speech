"""PPT 配音模块单元测试。

覆盖主要功能点、边界条件和异常情况，
使用 Python 标准 unittest 框架。
"""

import asyncio
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from edge_tts.exceptions import (
    NoAudioReceived,
    UnexpectedResponse,
    UnknownResponse,
    WebSocketError,
)
from lxml import etree as lxml_etree

from ppt_speech.notes_tts import (
    P_NS,
    P14_NS,
    PTSpeechConfig,
    _apply_autoplay_timing,
    _normalize_voice_name,
    _read_notes_text,
    embed_audio_autoplay,
    main,
    process_slides,
    text_to_mp3,
)


NSMAP = {"p": P_NS, "p14": P14_NS}


class TestPTSpeechConfig(unittest.TestCase):
    """PTSpeechConfig 配置类测试。"""

    def test_default_creation(self) -> None:
        """测试默认配置创建。"""
        config = PTSpeechConfig()
        self.assertEqual(config.input_dir, Path("data"))
        self.assertEqual(config.output_dir, Path("data"))
        self.assertEqual(config.input_filename, "input.pptx")
        self.assertEqual(config.output_filename, "output.pptx")
        self.assertEqual(config.voice_name, "zh-CN-XiaoxiaoNeural")
        self.assertEqual(config.speech_rate, "+0%")
        self.assertEqual(config.audio_icon_offset, -2.0)
        self.assertEqual(config.audio_icon_size, 1.0)

    def test_custom_creation(self) -> None:
        """测试自定义配置创建。"""
        config = PTSpeechConfig(
            input_dir=Path("input_dir"),
            output_dir=Path("output_dir"),
            input_filename="test.pptx",
            output_filename="result.pptx",
            voice_name="en-US-AriaNeural",
            speech_rate="-50%",
            temp_audio_dir=Path("custom_temp"),
            audio_icon_offset=-3.0,
            audio_icon_size=2.0,
        )
        self.assertEqual(config.input_dir, Path("input_dir"))
        self.assertEqual(config.voice_name, "en-US-AriaNeural")
        self.assertEqual(config.speech_rate, "-50%")
        self.assertEqual(config.audio_icon_offset, -3.0)
        self.assertEqual(config.audio_icon_size, 2.0)

    def test_input_path_property(self) -> None:
        """测试 input_path 属性。"""
        config = PTSpeechConfig(
            input_dir=Path("mydata"),
            input_filename="test.pptx",
        )
        self.assertEqual(config.input_path, Path("mydata/test.pptx"))

    def test_output_path_property(self) -> None:
        """测试 output_path 属性。"""
        config = PTSpeechConfig(
            output_dir=Path("out"),
            output_filename="result.pptx",
        )
        self.assertEqual(config.output_path, Path("out/result.pptx"))

    @patch("pathlib.Path.exists", return_value=True)
    def test_validate_valid(self, mock_exists: MagicMock) -> None:
        """测试合法配置验证。"""
        config = PTSpeechConfig()
        config.validate()

    def test_validate_invalid_voice(self) -> None:
        """测试无效语音名称验证。"""
        config = PTSpeechConfig(voice_name="invalid-voice")
        with self.assertRaises(ValueError) as ctx:
            config.validate()
        self.assertIn("语音名称格式错误", str(ctx.exception))

    @patch("pathlib.Path.exists", return_value=True)
    def test_validate_invalid_speech_rate(self, mock_exists: MagicMock) -> None:
        """测试无效语速验证。"""
        config = PTSpeechConfig(speech_rate="fast")
        with self.assertRaises(ValueError) as ctx:
            config.validate()
        self.assertIn("语速格式错误", str(ctx.exception))

    def test_validate_missing_input_file(self) -> None:
        """测试输入文件不存在验证。"""
        config = PTSpeechConfig(input_dir=Path("nonexistent"))
        with self.assertRaises(FileNotFoundError) as ctx:
            config.validate()
        self.assertIn("输入 PPT 文件不存在", str(ctx.exception))

    @patch("pathlib.Path.exists", return_value=True)
    def test_validate_boundary_speech_rates(self, mock_exists: MagicMock) -> None:
        """测试边界语速值验证。"""
        for rate in ("+0%", "-0%", "+100%", "-100%", "+999%"):
            config = PTSpeechConfig(speech_rate=rate)
            config.validate()


class TestNormalizeVoiceName(unittest.TestCase):
    """_normalize_voice_name 函数测试。"""

    def test_standard_chinese_voice(self) -> None:
        """测试标准中文语音名称规范化。"""
        result = _normalize_voice_name("zh-CN-XiaoxiaoNeural")
        self.assertEqual(
            result,
            "Microsoft Server Speech Text to Speech Voice"
            " (zh-CN, XiaoxiaoNeural)",
        )

    def test_standard_english_voice(self) -> None:
        """测试标准英文语音名称规范化。"""
        result = _normalize_voice_name("en-US-AriaNeural")
        self.assertEqual(
            result,
            "Microsoft Server Speech Text to Speech Voice"
            " (en-US, AriaNeural)",
        )

    def test_voice_with_region_suffix(self) -> None:
        """测试带地区后缀的语音名称规范化。"""
        result = _normalize_voice_name("zh-CN-Xiaoxiao-YunxiNeural")
        self.assertEqual(
            result,
            "Microsoft Server Speech Text to Speech Voice"
            " (zh-CN-Xiaoxiao, YunxiNeural)",
        )

    def test_already_full_format(self) -> None:
        """测试已为完整格式的语音名称。"""
        full_name = (
            "Microsoft Server Speech Text to Speech Voice"
            " (zh-CN, XiaoxiaoNeural)"
        )
        result = _normalize_voice_name(full_name)
        self.assertEqual(result, full_name)

    def test_non_standard_voice(self) -> None:
        """测试非标准格式的语音名称。"""
        result = _normalize_voice_name("SomeVoice")
        self.assertEqual(result, "SomeVoice")


class TestReadNotesText(unittest.TestCase):
    """_read_notes_text 函数测试。"""

    def setUp(self) -> None:
        self.mock_slide = MagicMock()

    def test_slide_with_notes(self) -> None:
        """测试有备注的幻灯片。"""
        mock_notes = MagicMock()
        mock_text_frame = MagicMock()
        mock_text_frame.text = "这是一段备注文字"
        mock_notes.notes_text_frame = mock_text_frame

        self.mock_slide.has_notes_slide = True
        self.mock_slide.notes_slide = mock_notes

        result = _read_notes_text(self.mock_slide)
        self.assertEqual(result, "这是一段备注文字")

    def test_slide_without_notes_slide(self) -> None:
        """测试无备注页的幻灯片。"""
        self.mock_slide.has_notes_slide = False
        result = _read_notes_text(self.mock_slide)
        self.assertEqual(result, "")

    def test_slide_with_empty_text_frame(self) -> None:
        """测试备注文本框为空的幻灯片。"""
        mock_notes = MagicMock()
        mock_notes.notes_text_frame = None

        self.mock_slide.has_notes_slide = True
        self.mock_slide.notes_slide = mock_notes

        result = _read_notes_text(self.mock_slide)
        self.assertEqual(result, "")

    def test_slide_with_whitespace_only_notes(self) -> None:
        """测试备注仅含空白字符的幻灯片。"""
        mock_notes = MagicMock()
        mock_text_frame = MagicMock()
        mock_text_frame.text = "   \n\t   "
        mock_notes.notes_text_frame = mock_text_frame

        self.mock_slide.has_notes_slide = True
        self.mock_slide.notes_slide = mock_notes

        result = _read_notes_text(self.mock_slide)
        self.assertEqual(result, "")


class TestTextToMP3(unittest.IsolatedAsyncioTestCase):
    """text_to_mp3 函数测试。"""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_empty_text_returns_false(self) -> None:
        """测试空文字返回 False。"""
        result = await text_to_mp3("", self.temp_dir / "test.mp3")
        self.assertFalse(result)

    async def test_whitespace_only_returns_false(self) -> None:
        """测试纯空白文字返回 False。"""
        result = await text_to_mp3(
            "   \n\t   ", self.temp_dir / "test.mp3"
        )
        self.assertFalse(result)

    async def test_invalid_speech_rate_raises(self) -> None:
        """测试无效语速抛出 ValueError。"""
        with self.assertRaises(ValueError) as ctx:
            await text_to_mp3(
                "测试文字",
                self.temp_dir / "test.mp3",
                speech_rate="invalid",
            )
        self.assertIn("语速格式错误", str(ctx.exception))

    @patch("ppt_speech.tts_client.Communicate")
    async def test_successful_conversion(
        self, mock_communicate_class: MagicMock
    ) -> None:
        """测试成功转换。"""
        mock_comm = AsyncMock()
        mock_communicate_class.return_value = mock_comm

        result = await text_to_mp3(
            "测试文字",
            self.temp_dir / "test.mp3",
            voice_name="zh-CN-XiaoxiaoNeural",
            speech_rate="+50%",
        )

        self.assertTrue(result)
        mock_communicate_class.assert_called_once()
        mock_comm.save.assert_called_once()

    @patch("ppt_speech.tts_client.Communicate")
    async def test_no_audio_received_handling(
        self, mock_communicate_class: MagicMock
    ) -> None:
        """测试 NoAudioReceived 异常处理。"""
        from edge_tts.exceptions import EdgeTTSException

        mock_comm = AsyncMock()
        mock_comm.save.side_effect = NoAudioReceived("无音频")
        mock_communicate_class.return_value = mock_comm

        with self.assertRaises(EdgeTTSException):
            await text_to_mp3("测试文字", self.temp_dir / "test.mp3")

    @patch("ppt_speech.tts_client.Communicate")
    async def test_unexpected_response_handling(
        self, mock_communicate_class: MagicMock
    ) -> None:
        """测试 UnexpectedResponse 异常处理。"""
        from edge_tts.exceptions import EdgeTTSException

        mock_comm = AsyncMock()
        mock_comm.save.side_effect = UnexpectedResponse("意外响应")
        mock_communicate_class.return_value = mock_comm

        with self.assertRaises(EdgeTTSException):
            await text_to_mp3("测试文字", self.temp_dir / "test.mp3")

    @patch("ppt_speech.tts_client.Communicate")
    async def test_unknown_response_handling(
        self, mock_communicate_class: MagicMock
    ) -> None:
        """测试 UnknownResponse 异常处理。"""
        from edge_tts.exceptions import EdgeTTSException

        mock_comm = AsyncMock()
        mock_comm.save.side_effect = UnknownResponse("未知响应")
        mock_communicate_class.return_value = mock_comm

        with self.assertRaises(EdgeTTSException):
            await text_to_mp3("测试文字", self.temp_dir / "test.mp3")

    @patch("ppt_speech.tts_client.Communicate")
    async def test_websocket_error_handling(
        self, mock_communicate_class: MagicMock
    ) -> None:
        """测试 WebSocketError 异常处理。"""
        from edge_tts.exceptions import EdgeTTSException

        mock_comm = AsyncMock()
        mock_comm.save.side_effect = WebSocketError("连接错误")
        mock_communicate_class.return_value = mock_comm

        with self.assertRaises(EdgeTTSException):
            await text_to_mp3("测试文字", self.temp_dir / "test.mp3")

    @patch("ppt_speech.tts_client.Communicate")
    async def test_os_error_handling(
        self, mock_communicate_class: MagicMock
    ) -> None:
        """测试 OS 错误处理。"""
        mock_comm = AsyncMock()
        mock_comm.save.side_effect = OSError("磁盘错误")
        mock_communicate_class.return_value = mock_comm

        with self.assertRaises(OSError) as ctx:
            await text_to_mp3("测试文字", self.temp_dir / "test.mp3")
        self.assertIn("磁盘错误", str(ctx.exception))

    @patch("ppt_speech.tts_client.Communicate")
    async def test_custom_voice_and_rate(
        self, mock_communicate_class: MagicMock
    ) -> None:
        """测试自定义语音和语速。"""
        mock_comm = AsyncMock()
        mock_communicate_class.return_value = mock_comm

        result = await text_to_mp3(
            "测试",
            self.temp_dir / "test.mp3",
            voice_name="en-US-AriaNeural",
            speech_rate="-30%",
        )

        self.assertTrue(result)
        call_args = mock_communicate_class.call_args
        self.assertIn("AriaNeural", call_args[0][1])
        self.assertEqual(call_args[1]["rate"], "-30%")

    @patch("ppt_speech.tts_client.Communicate")
    async def test_creates_parent_directory(
        self, mock_communicate_class: MagicMock
    ) -> None:
        """测试自动创建父目录。"""
        mock_comm = AsyncMock()
        mock_communicate_class.return_value = mock_comm

        deep_path = self.temp_dir / "a" / "b" / "c" / "test.mp3"
        await text_to_mp3("测试", deep_path)

        self.assertTrue(deep_path.parent.exists())


class TestApplyAutoplayTiming(unittest.TestCase):
    """_apply_autoplay_timing 函数测试。"""

    def test_xml_with_timing(self) -> None:
        """测试有时序 XML 的修改。"""
        xml_str = (
            f'<p:sld xmlns:p="{P_NS}" xmlns:p14="{P14_NS}">'
            f"<p:timing>"
            f"<p:tnLst>"
            f"<p:par>"
            f'<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
            f"<p:childTnLst>"
            f'<p:seq concurrent="1" nextAc="seek">'
            f'<p:cTn id="2" dur="indefinite" nodeType="mainSeq">'
            f"<p:childTnLst>"
            f"<p:par>"
            f'<p:cMediaNode volCtrl="100" muteVal="0">'
            f'<p:cTn id="3" fill="hold">'
            f"<p:stCondLst>"
            f'<p:cond delay="0"/>'
            f"</p:stCondLst>"
            f"</p:cTn>"
            f"</p:cMediaNode>"
            f"</p:par>"
            f"</p:childTnLst>"
            f"</p:cTn>"
            f"</p:seq>"
            f"</p:childTnLst>"
            f"</p:cTn>"
            f"</p:par>"
            f"</p:tnLst>"
            f"</p:timing>"
            f"</p:sld>"
        )

        element = lxml_etree.fromstring(xml_str.encode())
        _apply_autoplay_timing(element)

        media_nodes = element.findall(".//p:cMediaNode", NSMAP)
        self.assertTrue(len(media_nodes) > 0)
        for node in media_nodes:
            self.assertEqual(
                node.get(f"{{{P_NS}}}playOnEntry"), "1"
            )

        conds = element.findall(".//p:cond", NSMAP)
        for cond in conds:
            self.assertEqual(cond.get("delay"), "0")
            with_prev = cond.find(f"{{{P_NS}}}withPrev")
            self.assertIsNotNone(with_prev)

    def test_xml_without_timing(self) -> None:
        """测试无时序 XML 的处理。"""
        xml_str = f'<p:sld xmlns:p="{P_NS}"><p:someChild/></p:sld>'
        element = lxml_etree.fromstring(xml_str.encode())

        _apply_autoplay_timing(element)

        self.assertEqual(element.tag.split("}")[-1], "sld")

    def test_xml_with_media_elements(self) -> None:
        """测试媒体元素的 playOnEntry 设置。"""
        xml_str = (
            f'<p:sld xmlns:p="{P_NS}" xmlns:p14="{P14_NS}">'
            f"<p:p14BlipFill>"
            f"<p14:media>"
            f"</p14:media>"
            f"</p:p14BlipFill>"
            f"</p:sld>"
        )

        element = lxml_etree.fromstring(xml_str.encode())
        _apply_autoplay_timing(element)

        media_elements = list(element.iter(f"{{{P14_NS}}}media"))
        self.assertTrue(len(media_elements) > 0)
        for media_el in media_elements:
            self.assertEqual(
                media_el.get(f"{{{P_NS}}}playOnEntry"), "1"
            )


class TestEmbedAudioAutoplay(unittest.TestCase):
    """embed_audio_autoplay 函数测试。"""

    def setUp(self) -> None:
        self.mock_slide = MagicMock()
        self.mock_slide._element = MagicMock()
        self.mock_slide.shapes = MagicMock()

        self.temp_dir = Path(tempfile.mkdtemp())
        self.audio_path = self.temp_dir / "test.mp3"
        self.audio_path.write_bytes(b"fake audio content")

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_successful_embedding(self) -> None:
        """测试成功嵌入音频。"""
        embed_audio_autoplay(self.mock_slide, self.audio_path)

        self.mock_slide.shapes.add_movie.assert_called_once()
        call_args = self.mock_slide.shapes.add_movie.call_args
        self.assertIn(str(self.audio_path), call_args[0])

    def test_file_not_found(self) -> None:
        """测试音频文件不存在异常。"""
        nonexistent_path = self.temp_dir / "nonexistent.mp3"
        with self.assertRaises(FileNotFoundError) as ctx:
            embed_audio_autoplay(self.mock_slide, nonexistent_path)
        self.assertIn("音频文件不存在", str(ctx.exception))

    def test_invalid_icon_size(self) -> None:
        """测试无效图标尺寸异常。"""
        with self.assertRaises(ValueError) as ctx:
            embed_audio_autoplay(
                self.mock_slide, self.audio_path, icon_size=0
            )
        self.assertIn("图标尺寸必须为正数", str(ctx.exception))

    def test_negative_icon_size_raises(self) -> None:
        """测试负图标尺寸异常。"""
        with self.assertRaises(ValueError):
            embed_audio_autoplay(
                self.mock_slide, self.audio_path, icon_size=-1.0
            )

    def test_custom_icon_parameters(self) -> None:
        """测试自定义图标参数。"""
        embed_audio_autoplay(
            self.mock_slide,
            self.audio_path,
            icon_offset=-3.0,
            icon_size=2.0,
        )

        call_kwargs = self.mock_slide.shapes.add_movie.call_args[1]
        self.assertIn("left", call_kwargs)
        self.assertIn("width", call_kwargs)


class TestProcessSlides(unittest.IsolatedAsyncioTestCase):
    """process_slides 函数测试。"""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = PTSpeechConfig(
            input_dir=self.temp_dir,
            output_dir=self.temp_dir,
            input_filename="input.pptx",
            output_filename="output.pptx",
            temp_audio_dir=self.temp_dir / "temp_audio",
        )

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("ppt_speech.notes_tts.embed_audio_autoplay")
    @patch("ppt_speech.notes_tts.text_to_mp3", new_callable=AsyncMock)
    @patch("ppt_speech.notes_tts._read_notes_text")
    async def test_process_with_notes(
        self,
        mock_read_notes: MagicMock,
        mock_text_to_mp3: AsyncMock,
        mock_embed: MagicMock,
    ) -> None:
        """测试处理有备注的幻灯片。"""
        mock_read_notes.return_value = "测试备注文字"
        mock_text_to_mp3.return_value = True

        mock_slide = MagicMock()
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        await process_slides(mock_prs, self.config)

        mock_text_to_mp3.assert_called_once_with(
            "测试备注文字",
            self.config.temp_audio_dir / "slide_1.mp3",
            voice_name=self.config.voice_name,
            speech_rate=self.config.speech_rate,
        )
        mock_embed.assert_called_once()
        mock_prs.save.assert_called_once()

    @patch("ppt_speech.notes_tts.embed_audio_autoplay")
    @patch("ppt_speech.notes_tts.text_to_mp3", new_callable=AsyncMock)
    @patch("ppt_speech.notes_tts._read_notes_text")
    async def test_process_without_notes(
        self,
        mock_read_notes: MagicMock,
        mock_text_to_mp3: AsyncMock,
        mock_embed: MagicMock,
    ) -> None:
        """测试处理无备注的幻灯片。"""
        mock_read_notes.return_value = ""

        mock_slide = MagicMock()
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        await process_slides(mock_prs, self.config)

        mock_text_to_mp3.assert_not_called()
        mock_embed.assert_not_called()
        mock_prs.save.assert_called_once()

    @patch("ppt_speech.notes_tts.embed_audio_autoplay")
    @patch("ppt_speech.notes_tts.text_to_mp3", new_callable=AsyncMock)
    @patch("ppt_speech.notes_tts._read_notes_text")
    async def test_process_multiple_slides(
        self,
        mock_read_notes: MagicMock,
        mock_text_to_mp3: AsyncMock,
        mock_embed: MagicMock,
    ) -> None:
        """测试处理多个幻灯片。"""
        mock_read_notes.side_effect = [
            "第一页备注",
            "",
            "第三页备注",
        ]
        mock_text_to_mp3.return_value = True

        mock_slides = [MagicMock(), MagicMock(), MagicMock()]
        mock_prs = MagicMock()
        mock_prs.slides = mock_slides

        await process_slides(mock_prs, self.config)

        self.assertEqual(mock_text_to_mp3.call_count, 2)
        self.assertEqual(mock_embed.call_count, 2)
        mock_prs.save.assert_called_once()

    @patch("ppt_speech.notes_tts.embed_audio_autoplay")
    @patch("ppt_speech.notes_tts.text_to_mp3", new_callable=AsyncMock)
    @patch("ppt_speech.notes_tts._read_notes_text")
    async def test_temp_dir_cleanup_on_success(
        self,
        mock_read_notes: MagicMock,
        mock_text_to_mp3: AsyncMock,
        mock_embed: MagicMock,
    ) -> None:
        """测试成功处理后临时目录清理。"""
        mock_read_notes.return_value = "测试"
        mock_text_to_mp3.return_value = True

        mock_slide = MagicMock()
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        self.config.temp_audio_dir.mkdir(parents=True, exist_ok=True)

        await process_slides(mock_prs, self.config)

        self.assertFalse(self.config.temp_audio_dir.exists())

    @patch("ppt_speech.notes_tts.embed_audio_autoplay")
    @patch("ppt_speech.notes_tts.text_to_mp3", new_callable=AsyncMock)
    @patch("ppt_speech.notes_tts._read_notes_text")
    async def test_temp_dir_cleanup_on_failure(
        self,
        mock_read_notes: MagicMock,
        mock_text_to_mp3: AsyncMock,
        mock_embed: MagicMock,
    ) -> None:
        """测试处理失败后临时目录清理。"""
        mock_read_notes.return_value = "测试"
        mock_text_to_mp3.side_effect = RuntimeError("处理失败")

        mock_slide = MagicMock()
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        self.config.temp_audio_dir.mkdir(parents=True, exist_ok=True)

        with self.assertRaises(RuntimeError):
            await process_slides(mock_prs, self.config)

        self.assertFalse(self.config.temp_audio_dir.exists())

    @patch("ppt_speech.notes_tts.embed_audio_autoplay")
    @patch("ppt_speech.notes_tts.text_to_mp3", new_callable=AsyncMock)
    @patch("ppt_speech.notes_tts._read_notes_text")
    async def test_tts_failure_skips_embed(
        self,
        mock_read_notes: MagicMock,
        mock_text_to_mp3: AsyncMock,
        mock_embed: MagicMock,
    ) -> None:
        """测试 TTS 失败时跳过嵌入。"""
        mock_read_notes.return_value = "测试"
        mock_text_to_mp3.return_value = False

        mock_slide = MagicMock()
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        await process_slides(mock_prs, self.config)

        mock_embed.assert_not_called()


class TestMain(unittest.IsolatedAsyncioTestCase):
    """main 函数测试。"""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.input_path = self.temp_dir / "input.pptx"
        self.input_path.write_bytes(b"fake pptx content")

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("ppt_speech.notes_tts.process_slides", new_callable=AsyncMock)
    @patch("ppt_speech.notes_tts.Presentation")
    async def test_main_with_custom_config(
        self,
        mock_presentation: MagicMock,
        mock_process: AsyncMock,
    ) -> None:
        """测试使用自定义配置运行。"""
        mock_prs = MagicMock()
        mock_presentation.return_value = mock_prs

        config = PTSpeechConfig(
            input_dir=self.temp_dir,
            output_dir=self.temp_dir,
            input_filename="input.pptx",
            output_filename="output.pptx",
        )

        await main(config)

        mock_presentation.assert_called_once_with(str(self.input_path))
        mock_process.assert_called_once_with(mock_prs, config)

    @patch("ppt_speech.notes_tts.process_slides", new_callable=AsyncMock)
    @patch("ppt_speech.notes_tts.Presentation")
    async def test_main_with_default_config(
        self,
        mock_presentation: MagicMock,
        mock_process: AsyncMock,
    ) -> None:
        """测试使用默认配置运行。"""
        mock_prs = MagicMock()
        mock_presentation.return_value = mock_prs

        with patch.object(
            PTSpeechConfig, "validate", return_value=None
        ):
            with patch.object(
                PTSpeechConfig,
                "input_path",
                new_callable=PropertyMock,
                return_value=self.input_path,
            ):
                await main()

        mock_presentation.assert_called_once()
        mock_process.assert_called_once()

    async def test_main_propagates_validation_error(self) -> None:
        """测试 main 函数传播验证错误。"""
        config = PTSpeechConfig(
            input_dir=Path("nonexistent_dir"),
        )
        with self.assertRaises(FileNotFoundError):
            await main(config)


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    """集成测试：验证模块间协作。"""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_paths_combined_correctly(self) -> None:
        """测试配置路径正确组合。"""
        config = PTSpeechConfig(
            input_dir=Path("inputs"),
            output_dir=Path("outputs"),
            input_filename="presentation.pptx",
            output_filename="result.pptx",
        )
        self.assertEqual(
            config.input_path, Path("inputs/presentation.pptx")
        )
        self.assertEqual(
            config.output_path, Path("outputs/result.pptx")
        )

    def test_voice_normalization_roundtrip(self) -> None:
        """测试语音名称规范化往返。"""
        short_name = "zh-CN-XiaoxiaoNeural"
        full_name = _normalize_voice_name(short_name)
        self.assertIn("Microsoft Server Speech Text to Speech Voice", full_name)
        self.assertIn("zh-CN", full_name)
        self.assertIn("XiaoxiaoNeural", full_name)

    def test_voice_normalization_with_region(self) -> None:
        """测试带地区的语音名称规范化。"""
        short_name = "en-US-AriaNeural"
        full_name = _normalize_voice_name(short_name)
        self.assertIn("en-US", full_name)
        self.assertIn("AriaNeural", full_name)

    @patch("ppt_speech.notes_tts.Presentation")
    @patch("ppt_speech.notes_tts.embed_audio_autoplay")
    @patch("ppt_speech.notes_tts._read_notes_text")
    @patch("ppt_speech.notes_tts.text_to_mp3", new_callable=AsyncMock)
    async def test_full_pipeline_mock(
        self,
        mock_text_to_mp3: AsyncMock,
        mock_read_notes: MagicMock,
        mock_embed: MagicMock,
        mock_presentation: MagicMock,
    ) -> None:
        """测试完整流水线（使用 mock）。"""
        mock_read_notes.return_value = "集成测试备注"
        mock_text_to_mp3.return_value = True

        mock_slide = MagicMock()
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]
        mock_presentation.return_value = mock_prs

        input_path = self.temp_dir / "input.pptx"
        input_path.write_bytes(b"fake")

        config = PTSpeechConfig(
            input_dir=self.temp_dir,
            output_dir=self.temp_dir,
            input_filename="input.pptx",
            output_filename="output.pptx",
        )

        await main(config)

        mock_text_to_mp3.assert_called_once()
        mock_embed.assert_called_once()
        mock_prs.save.assert_called_once_with(str(config.output_path))
        self.assertFalse(config.temp_audio_dir.exists())


if __name__ == "__main__":
    unittest.main()