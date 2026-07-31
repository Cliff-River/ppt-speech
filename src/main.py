import asyncio

from ppt_speech import notes_tts
from ppt_speech.tts_client import get_voices_list
import json

voices = asyncio.run(get_voices_list())
with open("voices.json", "w", encoding="utf-8") as f:
    json.dump(voices, f, ensure_ascii=False, indent=4)
