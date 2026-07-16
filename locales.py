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
            "/digest — объявления из базы по фильтру\n"
            "/stop — остановить уведомления\n"
            "/feedback — написать мне напрямую\n"
            "/help — все команды\n\n"
            "⚠️ Кнопка «Связь с автором» — только для вопросов, не для поиска квартир.\n\n"
            "Начнём? Настрой фильтр командой /filter"
        ),

        # --- FSM: настройка фильтра ---
        "ask_city": "🏙 Введи город (например: Brno, Praha)\nИли напиши «любой» чтобы получать из всех городов:",
        "ask_price_min": "💰 Минимальная цена (Kč)?\nИли напиши «0» если без ограничений:",
        "ask_price_max": "💰 Максимальная цена (Kč)?\nИли напиши «0» если без ограничений:",
        "ask_property_type": "🏠 Тип недвижимости:",
        "type_flat": "🏠 Квартира",
        "type_room": "🛏 Комната / подселение",
        "type_house": "🏡 Дом",
        "type_any": "🔍 Всё подряд",
        "type_use_buttons": "👇 Выбери тип кнопкой ниже. Если кнопок не видно — нажми значок ▦ справа от поля ввода.",
        "edit_city_btn": "🏙 Изменить город",
        "edit_price_btn": "💰 Изменить цену",
        "edit_type_btn": "🏠 Изменить тип",
        "filter_updated": "✅ Фильтр обновлён:\n\n🏙 Город: {city}\n💰 Цена: {price}\n🏠 Тип: {type}",

        # --- Валидация города ---
        "city_not_valid": "⚠️ Это не похоже на город. Введи название, например: Brno, Praha, Ostrava\nИли напиши «любой» — буду слать из всех городов.",
        "city_unknown": "⚠️ Города «{city}» я не знаю. Проверь написание или напиши «любой».",
        "city_did_you_mean": "🤔 Не знаю такого города. Может, ты имел в виду «{suggestion}»?\nНапиши правильно или «любой».",

        # --- Валидация цены ---
        "price_not_a_number": "⚠️ Введи число, например: 15000 (или 0 — без ограничений).",
        "price_too_high": "🤨 {price:,} Kč в месяц? Ты ебанулся или это вилла с прислугой?\nАренда в Чехии — до {max:,} Kč. Введи реальную цену.",
        "price_too_low": "🤨 {price:,} Kč в месяц — это цена кофе, а не квартиры.\nМинимум {min:,} Kč. Или напиши 0, если без ограничений.",
        "price_sanity": "🤔 {price:,} Kč? По базе средняя цена тут около {median:,} Kč. Точно не перепутал?",
        "price_confirm_yes": "✅ Да, всё верно",
        "price_confirm_no": "✏️ Ввести заново",
        # --- Фильтр ---
        "filter_saved": "✅ Фильтр сохранён:\n\n🏙 Город: {city}\n💰 Цена: {price}\n🏠 Тип: {type}\n\nЖди уведомлений!",
        "your_filter": "📋 Твой фильтр:\n\n🏙 Город: {city}\n💰 Цена: {price}\n🏠 Тип: {type}",
        "price_range": "от {min:,} до {max:,} Kč",
        "price_from": "от {min:,} Kč",
        "price_to": "до {max:,} Kč",
        "price_any": "любая",
        "no_filter": "У тебя нет активного фильтра. Настрой через /filter",
        "any": "любой",
        "any_type": "всё подряд",
        "stopped": "🔕 Уведомления остановлены. Вернуться можно через /filter",

        # --- Кнопки / служебное ---
        "share_button": "🔥 Рассказать другу",
        "feedback_button": "💬 Связь с автором",
        "remind_filter": "👋 Эй, не забудь настроить фильтр!\n\nБез него уведомления не придут.\nПросто напиши /filter и укажи город и цену — займёт 30 секунд.",
        "cancelled": "❌ Отменено.",
        "nothing_to_cancel": "Нечего отменять.",
        "help": (
            "📌 Команды RealtyKelev Bot:\n\n"
            "/filter — настроить фильтр (город, цена, тип)\n"
            "/myfilter — показать текущий фильтр\n"
            "/digest — объявления из базы по фильтру\n"
            "/stop — остановить уведомления\n"
            "/feedback — написать мне напрямую\n"
            "/cancel — отменить текущее действие\n"
            "/help — это сообщение\n\n"
            "⚡ Как работает: каждые 10 секунд проверяю новые объявления на 13 чешских сайтах "
            "и шлю ссылку, как только появится что-то под твой фильтр.\n\n"
            "⚠️ Квартиры я не ищу вручную и на «а есть что-нибудь?» не отвечаю — это делает фильтр."
        ),
    },
    "cs": {
        "choose_language": "👋 Ahoj! Vyber si jazyk:",
        "language_set": "✅ Jazyk nastaven: Čeština",
        "welcome": (
            "👋 Ahoj! Jsem RealtyKelev Bot.\n\n"
            "⚡ Jak funguju:\n"
            "Každých 10 sekund kontroluji nové nabídky nemovitostí na českých webech "
            "a hned ti pošlu odkaz — dozvíš se jako první.\n\n"
            "Neukládám texty inzerátů — pouze odkazy na originál.\n\n"
            "📌 Příkazy:\n"
            "/filter — nastavit filtr (město, cena, typ)\n"
            "/myfilter — zobrazit aktuální filtr\n"
            "/digest — inzeráty z databáze podle filtru\n"
            "/stop — zastavit upozornění\n"
            "/feedback — napsat mi přímo\n"
            "/help — všechny příkazy\n\n"
            "⚠️ Tlačítko «Kontakt s autorem» — pouze pro dotazy, ne pro hledání bytů.\n\n"
            "Začneme? Nastav filtr příkazem /filter"
        ),

        # --- FSM: nastavení filtru ---
        "ask_city": "🏙 Zadej město (např. Brno, Praha)\nNebo napiš „libovolné“ pro všechna města:",
        "ask_price_min": "💰 Minimální cena (Kč)?\nNebo napiš „0“ pro bez omezení:",
        "ask_price_max": "💰 Maximální cena (Kč)?\nNebo napiš „0“ pro bez omezení:",
        "ask_property_type": "🏠 Typ nemovitosti:",
        "type_flat": "🏠 Byt",
        "type_room": "🛏 Pokoj / spolubydlení",
        "type_house": "🏡 Dům",
        "type_any": "🔍 Vše",
        "type_use_buttons": "👇 Vyber typ tlačítkem níže. Pokud tlačítka nevidíš — klikni na ikonu ▦ vpravo od pole pro zadávání.",
        "edit_city_btn": "🏙 Změnit město",
        "edit_price_btn": "💰 Změnit cenu",
        "edit_type_btn": "🏠 Změnit typ",
        "filter_updated": "✅ Filtr aktualizován:\n\n🏙 Město: {city}\n💰 Cena: {price}\n🏠 Typ: {type}",

        # --- Validace města ---
        "city_not_valid": "⚠️ Tohle nevypadá jako město. Zadej název, např.: Brno, Praha, Ostrava\nNebo napiš „libovolné“ — budu posílat ze všech měst.",
        "city_unknown": "⚠️ Město „{city}“ neznám. Zkontroluj pravopis nebo napiš „libovolné“.",
        "city_did_you_mean": "🤔 Takové město neznám. Nemyslel jsi „{suggestion}“?\nNapiš to správně nebo „libovolné“.",

        # --- Validace ceny ---
        "price_not_a_number": "⚠️ Zadej číslo, například: 15000 (nebo 0 — bez omezení).",
        "price_too_high": "🤨 {price:,} Kč měsíčně? To už není nájem, to je vila se služebnictvem.\nNájem v ČR je do {max:,} Kč. Zadej reálnou cenu.",
        "price_too_low": "🤨 {price:,} Kč měsíčně — to je cena kávy, ne bytu.\nMinimum je {min:,} Kč. Nebo napiš 0, pokud bez omezení.",
        "price_sanity": "🤔 {price:,} Kč? Podle databáze je průměrná cena tady kolem {median:,} Kč. Nespletl sis to?",
        "price_confirm_yes": "✅ Ano, je to správně",
        "price_confirm_no": "✏️ Zadat znovu",

        # --- Filtr ---
        "filter_saved": "✅ Filtr uložen:\n\n🏙 Město: {city}\n💰 Cena: {price}\n🏠 Typ: {type}\n\nČekej na upozornění!",
        "your_filter": "📋 Tvůj filtr:\n\n🏙 Město: {city}\n💰 Cena: {price}\n🏠 Typ: {type}",
        "price_range": "od {min:,} do {max:,} Kč",
        "price_from": "od {min:,} Kč",
        "price_to": "do {max:,} Kč",
        "price_any": "libovolná",
        "no_filter": "Nemáš aktivní filtr. Nastav přes /filter",
        "any": "libovolné",
        "any_type": "vše",
        "stopped": "🔕 Upozornění zastavena. Vrátit se můžeš přes /filter",

        # --- Tlačítka / systémové ---
        "share_button": "🔥 Doporučit příteli",
        "feedback_button": "💬 Kontakt s autorem",
        "remind_filter": "👋 Hej, nezapomeň nastavit filtr!\n\nBez něj upozornění nepřijdou.\nNapiš /filter a zadej město a cenu — zabere to 30 sekund.",
        "cancelled": "❌ Zrušeno.",
        "nothing_to_cancel": "Není co rušit.",
        "help": (
            "📌 Příkazy RealtyKelev Bot:\n\n"
            "/filter — nastavit filtr (město, cena, typ)\n"
            "/myfilter — zobrazit aktuální filtr\n"
            "/digest — inzeráty z databáze podle filtru\n"
            "/stop — zastavit upozornění\n"
            "/feedback — napsat mi přímo\n"
            "/cancel — zrušit aktuální akci\n"
            "/help — tato zpráva\n\n"
            "⚡ Jak to funguje: každých 10 sekund kontroluji nové inzeráty na 13 českých webech "
            "a jakmile se objeví něco podle tvého filtru, pošlu odkaz.\n\n"
            "⚠️ Byty nehledám ručně a na „máš něco?“ neodpovídám — to dělá filtr."
        ),
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    lang = lang if lang in TEXTS else "ru"
    text = TEXTS[lang].get(key)
    if text is None:
        # Ключа нет — не молчим, а орём в логи. Иначе пользователь увидит "price_too_high".
        print(f"[locales] ⚠️ MISSING KEY: '{key}' (lang={lang})")
        return f"[missing:{key}]"
    return text.format(**kwargs) if kwargs else text