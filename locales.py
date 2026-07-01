TEXTS = {
    "ru": {
        "choose_language": "👋 Привет! Выбери язык:",
        "language_set": "✅ Язык установлен: Русский",
        "welcome": (
            "👋 Привет! Я RealtyKelev Bot.\n\n"
            "⚡ Как я работаю:\n"
            "Каждые 10 секунд я проверяю новые объявления на чешских сайтах недвижимости "
            "и сразу отправляю тебе ссылку — ты узнаёшь раньше всех.\n\n"
            "Я не храню тексты объявлений — только ссылки на оригинал.\n\n"
            "📌 Команды:\n"
            "/filter — настроить фильтр (город, цена, тип)\n"
            "/myfilter — посмотреть текущий фильтр\n"
            "/stop — остановить уведомления\n"
            "/feedback — написать мне напрямую\n\n"
            "⚠️ Кнопка «Связь с автором» — только для вопросов, не для поиска квартир.\n\n"
            "Начнём? Настрой фильтр командой /filter"
        ),
        "ask_city": "🏙 Введи город (например: Brno, Praha)\nИли напиши «любой» чтобы получать из всех городов:",
        "ask_price_min": "💰 Минимальная цена (Kč)?\nИли напиши «0» если без ограничений:",
        "ask_price_max": "💰 Максимальная цена (Kč)?\nИли напиши «0» если без ограничений:",
        "ask_property_type": "🏠 Тип недвижимости:",
        "type_flat": "🏠 Квартира",
        "type_room": "🛏 Комната / подселение",
        "type_house": "🏡 Дом",
        "type_any": "🔍 Всё подряд",
        "filter_saved": "✅ Фильтр сохранён:\n\n🏙 Город: {city}\n💰 Цена: {price_min} — {price_max} Kč\n🏠 Тип: {type}\n\nЖди уведомлений!",
        "any": "любой",
        "any_type": "всё подряд",
        "no_filter": "У тебя нет активного фильтра. Настрой через /filter",
        "your_filter": "📋 Твой фильтр:\n\n🏙 Город: {city}\n💰 Цена: {price_min} — {price_max} Kč\n🏠 Тип: {type}",
        "stopped": "🔕 Уведомления остановлены. Вернуться можно через /filter",
        "share_button": "🔥 Рассказать другу",
        "feedback_button": "💬 Связь с автором",
        "remind_filter": "👋 Эй, не забудь настроить фильтр!\n\nБез него уведомления не придут.\nПросто напиши /filter и укажи город и цену — займёт 30 секунд.",
    },
    "cs": {
        "choose_language": "👋 Ahoj! Vyber si jazyk:",
        "language_set": "✅ Jazyk nastaven: Čeština",
        "welcome": (
            "👋 Ahoj! Jsem RealtyKelev Bot.\n\n"
            "⚡ Jak fungovám:\n"
            "Každých 10 sekund kontroluji nové nabídky nemovitostí na českých webech "
            "a hned ti pošlu odkaz — dozvíš se jako první.\n\n"
            "Neukládám texty inzerátů — pouze odkazy na originál.\n\n"
            "📌 Příkazy:\n"
            "/filter — nastavit filtr (město, cena, typ)\n"
            "/myfilter — zobrazit aktuální filtr\n"
            "/stop — zastavit upozornění\n"
            "/feedback — napsat mi přímo\n\n"
            "⚠️ Tlačítko «Kontakt s autorem» — pouze pro dotazy, ne pro hledání bytů.\n\n"
            "Začneme? Nastav filtr příkazem /filter"
        ),
        "ask_city": "🏙 Zadej město (např. Brno, Praha)\nNebo napiš „libovolné“ pro všechna města:",
        "ask_price_min": "💰 Minimální cena (Kč)?\nNebo napiš „0“ pro bez omezení:",
        "ask_price_max": "💰 Maximální cena (Kč)?\nNebo napiš „0“ pro bez omezení:",
        "ask_property_type": "🏠 Typ nemovitosti:",
        "type_flat": "🏠 Byt",
        "type_room": "🛏 Pokoj / spolubydlení",
        "type_house": "🏡 Dům",
        "type_any": "🔍 Vše",
        "filter_saved": "✅ Filtr uložen:\n\n🏙 Město: {city}\n💰 Cena: {price_min} — {price_max} Kč\n🏠 Typ: {type}\n\nČekej na upozornění!",
        "any": "libovolné",
        "any_type": "vše",
        "no_filter": "Nemáš aktivní filtr. Nastav přes /filter",
        "your_filter": "📋 Tvůj filtr:\n\n🏙 Město: {city}\n💰 Cena: {price_min} — {price_max} Kč\n🏠 Typ: {type}",
        "stopped": "🔕 Upozornění zastavena. Vrátit se můžeš přes /filter",
        "share_button": "🔥 Doporučit příteli",
        "feedback_button": "💬 Kontakt s autorem",
        "remind_filter": "👋 Hej, nezapomeň nastavit filtr!\n\nBez něj upozornění nepřijdou.\nNapiš /filter a zadej město a cenu — zabere to 30 sekund.",
    },
}

def t(lang: str, key: str, **kwargs) -> str:
    lang = lang if lang in TEXTS else "ru"
    text = TEXTS[lang].get(key, key)
    return text.format(**kwargs) if kwargs else text