import os
import json
import re
import time
from google import genai
from google.genai import types

MODEL = "gemini-3.5-flash-lite"

PROMPT = (
    "Ты — помощник Telegram-бота по аренде жилья в Чехии. Пользователь пишет или "
    "говорит на русском, украинском, суржике или чешском, часто с ошибками. "
    "Определи, чего он хочет, и верни СТРОГО JSON, без пояснений и markdown:\n"
    '{\n'
    '  "intent": "search | command | other",\n'
    '  "command": "если intent=command — одно из: start, filter, myfilter, digest, '
    'stop, feedback, help, admin, acheck, ausers, abandlist, abroadcast, aban, aunban, '
    'aclear, areply; иначе null",\n'
    '  "city": "город латиницей (Brno, Praha, Ostrava); район приводи к городу; иначе null",\n'
    '  "price_max": "макс. цена кронами числом или null",\n'
    '  "price_min": "мин. цена числом или null",\n'
    '  "property_type": "byt / pokoj / dum / null",\n'
    '  "rooms": "studio / 2 / 3 / 4 / null. 1+kk и гарсоньерка=studio; 2+kk,2+1=2; 3+kk,3+1=3; 4 и больше=4"\n'
    '}\n'
    "\n"
    "intent=search — запрос на поиск жилья («ищу двушку в брно до 15к»). "
    "Тогда заполни city/price/property_type/rooms.\n"
    "intent=command — просьба выполнить действие бота:\n"
    "  «покажи мой фильтр / что я искал» → myfilter;\n"
    "  «что в базе / покажи объявления» → digest;\n"
    "  «останови / хватит / отпишись / стоп уведомления» → stop;\n"
    "  «настроить фильтр вручную / поменять поиск» → filter;\n"
    "  «написать автору / связь с автором / пожаловаться» → feedback;\n"
    "  «помощь / команды / что умеешь» → help;\n"
    "  «начать / старт» → start;\n"
    "  админские: «статистика» → admin, «проверь парсеры» → acheck, «список юзеров» → ausers, "
    "«забаненные» → abandlist, «рассылка / разослать всем» → abroadcast, «забань» → aban, "
    "«разбань» → aunban, «почисти старые объявления» → aclear, «ответить юзеру» → areply.\n"
    "intent=other — всё остальное (болтовня, непонятное). Тогда command=null и поля фильтра null.\n"
    "city/price/rooms заполняй ТОЛЬКО при intent=search."
)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY"),
            http_options=types.HttpOptions(timeout=30000),
        )
    return _client


def _extract_json(raw):
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def extract_filter(text):
    """Текст запроса -> dict (intent/command/фильтр) или None при сбое."""
    last = None
    for attempt in range(3):
        try:
            resp = _get_client().models.generate_content(
                model=MODEL,
                contents=[PROMPT, text],
            )
            data = _extract_json(resp.text)
            if data is not None:
                return data
            last = "пустой ответ"
        except Exception as e:
            last = e
            print(f"[ai_extract] попытка {attempt + 1}: {e}")
        time.sleep(2)
    print(f"[ai_extract] не вышло: {last}")
    return None


def extract_filter_from_audio(audio_bytes, mime_type="audio/ogg"):
    """Голосовое (байты аудио) -> dict (intent/command/фильтр) или None."""
    last = None
    for attempt in range(3):
        try:
            resp = _get_client().models.generate_content(
                model=MODEL,
                contents=[
                    PROMPT,
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                ],
            )
            data = _extract_json(resp.text)
            if data is not None:
                return data
            last = "пустой ответ"
        except Exception as e:
            last = e
            print(f"[ai_extract audio] попытка {attempt + 1}: {e}")
        time.sleep(2)
    print(f"[ai_extract audio] не вышло: {last}")
    return None