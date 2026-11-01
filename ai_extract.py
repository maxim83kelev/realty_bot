
import os
import json
import re
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"

PROMPT = (
    "Ты парсер запросов на аренду жилья в Чехии. Пользователь пишет или говорит "
    "на русском, украинском, суржике или чешском, часто с ошибками и сокращениями. "
    "Извлеки параметры поиска. Верни СТРОГО JSON, без пояснений и markdown:\n"
    '{\n'
    '  "city": "город латиницей как в Чехии (Brno, Praha, Ostrava). '
    'Район (Královo Pole, Řečkovice, Vinohrady) приводи к его городу. Не назван — null",\n'
    '  "price_max": "макс. цена в кронах числом, или null",\n'
    '  "price_min": "мин. цена числом, или null",\n'
    '  "property_type": "byt / pokoj / dum / null",\n'
    '  "rooms": "studio / 2 / 3 / 4 / null. 1+kk и гарсоньерка=studio; 2+kk,2+1=2; 3+kk,3+1=3; 4 и больше=4"\n'
    '}'
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
    """Текст запроса -> dict с параметрами фильтра (или None при сбое)."""
    last = None
    for attempt in range(2):
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
    print(f"[ai_extract] не вышло: {last}")
    return None
