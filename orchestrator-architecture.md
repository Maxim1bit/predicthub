# Архитектура: Claude как Оркестратор инструментов

## КОНЦЕПЦИЯ

```
                    ┌─────────────────────┐
                    │    ТЫ (телефон)      │
                    │  Claude Dispatch     │
                    └─────────┬───────────┘
                              │ задача
                              ▼
                    ┌─────────────────────┐
                    │   CLAUDE COWORK     │
                    │   (мозг/менеджер)   │
                    │                     │
                    │  Принимает задачу   │
                    │  Разбивает на шаги  │
                    │  Вызывает нужные    │
                    │  инструменты        │
                    │  Проверяет результат│
                    └─────────┬───────────┘
                              │ вызывает
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │  MCP-серверы  │  │ Python-скрипты│  │  Внешние API │
   │ (инструменты) │  │  (автоматика) │  │  (сервисы)   │
   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
          │                 │                 │
    ┌─────┴─────┐    ┌─────┴─────┐    ┌─────┴─────┐
    │GSC Monitor│    │Trading Bot│    │Twitter API│
    │SEO Audit  │    │OBS Control│    │ElevenLabs │
    │Site Deploy│    │Video Gen  │    │Polymarket │
    │Competitor │    │Email Send │    │Telegram   │
    │Analytics  │    │Screenshot │    │YouTube API│
    └───────────┘    └───────────┘    └───────────┘
```

## ИНСТРУМЕНТЫ КОТОРЫЕ НУЖНО СОЗДАТЬ

---

### ИНСТРУМЕНТ 1: SEO-Монитор
**Что делает:** Автоматически собирает данные из Google Search Console
**Как Claude использует:** Вызывает → получает отчёт → принимает решение что обновить

**Реализация:** MCP-сервер (уже есть готовый: mcp-gsc)
```
Установка:
pip install mcp-gsc
# Добавить в claude config:
# claude mcp add gsc-monitor

Что Claude может запросить:
- "Покажи топ-20 запросов по кликам за неделю"
- "Какие страницы упали в позициях?"
- "Сколько кликов получила /polymarket/promo-code.html?"
```

**Стоимость:** Бесплатно (Google Search Console API)
**Сложность настройки:** Средняя (нужен Google Cloud проект + API ключи)

---

### ИНСТРУМЕНТ 2: Автопостер Twitter/X
**Что делает:** Публикует посты по команде Claude
**Как Claude использует:** Пишет текст → вызывает постер → пост опубликован

**Реализация:** Python-скрипт с Tweepy
```python
# tools/twitter_poster.py
import tweepy
import sys
import json

# Загружаем ключи из .env
client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET
)

def post_tweet(text, image_path=None):
    """Claude вызывает эту функцию через MCP или shell"""
    if image_path:
        auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
        api = tweepy.API(auth)
        media = api.media_upload(image_path)
        response = client.create_tweet(text=text, media_ids=[media.media_id])
    else:
        response = client.create_tweet(text=text)
    return response.data['id']

if __name__ == '__main__':
    text = sys.argv[1]
    tweet_id = post_tweet(text)
    print(json.dumps({"status": "posted", "tweet_id": tweet_id}))
```

**Claude вызывает так:**
```
"Запусти python tools/twitter_poster.py 'Polymarket just hit $3B
weekly volume. Here's why prediction markets are eating traditional
betting alive → [link]'"
```

**Стоимость:** Бесплатно (X API Free tier = 1500 постов/мес) или $100/мес (Basic = больше лимитов)
**Сложность:** Низкая

---

### ИНСТРУМЕНТ 3: Polymarket Trading Bot
**Что делает:** Торгует на Polymarket по стратегии
**Как Claude использует:** Анализирует рынки → решает что купить → отдаёт команду боту

**Реализация:** Python + Polymarket CLOB API
```python
# tools/poly_trader.py
from py_clob_client.client import ClobClient

client = ClobClient(
    host="https://clob.polymarket.com",
    key=PRIVATE_KEY,
    chain_id=137  # Polygon
)

def get_markets(keyword):
    """Получить рынки по ключевому слову"""
    markets = client.get_markets()
    return [m for m in markets if keyword.lower() in m['question'].lower()]

def buy_yes(token_id, amount, price):
    """Купить YES shares"""
    order = client.create_and_post_order(
        token_id=token_id,
        price=price,
        size=amount,
        side="BUY"
    )
    return order

def get_positions():
    """Текущие открытые позиции"""
    return client.get_positions()

def get_balance():
    """Баланс USDC"""
    return client.get_balance()
```

**Claude как торговый менеджер:**
```
Claude ежедневно:
1. Вызывает get_markets("bitcoin") → получает список рынков
2. Анализирует цены и новости
3. Решает: "BTC $200K к декабрю торгуется по $0.32, но новости
   позитивные. Покупаю 50 YES по $0.32"
4. Вызывает buy_yes(token_id, 50, 0.32)
5. Логирует сделку в /reports/trades.md
```

**Стоимость:** Бесплатно (API) + капитал для торговли ($500+)
**Сложность:** Средняя (нужен кошелёк с USDC)

---

### ИНСТРУМЕНТ 4: Видео-генератор (YouTube контент)
**Что делает:** Из текста → голос → видео
**Как Claude использует:** Пишет скрипт → отдаёт на озвучку → собирает видео

**Реализация:** Python + ElevenLabs + MoviePy
```python
# tools/video_maker.py
from elevenlabs import ElevenLabs
from moviepy.editor import *
import json

client = ElevenLabs(api_key=ELEVEN_API_KEY)

def text_to_audio(text, output_path="output.mp3"):
    """Озвучка текста"""
    audio = client.text_to_speech.convert(
        text=text,
        voice_id="YOUR_VOICE_ID",  # Клонированный или стандартный
        model_id="eleven_multilingual_v2"
    )
    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    return output_path

def make_video(audio_path, slides_dir, output="final.mp4"):
    """Собирает видео из аудио + слайдов"""
    audio = AudioFileClip(audio_path)
    # Загрузить слайды и разложить по таймингу
    clips = []
    for img in sorted(os.listdir(slides_dir)):
        clip = ImageClip(os.path.join(slides_dir, img)).set_duration(10)
        clips.append(clip)
    video = concatenate_videoclips(clips)
    video = video.set_audio(audio)
    video.write_videofile(output, fps=24)
    return output
```

**Claude как продюсер:**
```
1. Claude пишет скрипт видео "Top 5 Polymarket Markets This Week"
2. Вызывает text_to_audio(script) → получает MP3
3. Генерирует слайды (или Claude создаёт HTML → скриншотит)
4. Вызывает make_video() → получает MP4
5. (Опционально) загружает на YouTube через API
```

**Стоимость:** ElevenLabs $5/мес (Starter) или $22/мес (Creator)
**Сложность:** Средняя

---

### ИНСТРУМЕНТ 5: Стрим-менеджер (OBS Controller)
**Что делает:** Управляет OBS — переключает сцены, обновляет оверлеи
**Как Claude использует:** Перед/во время стрима обновляет данные на экране

**Реализация:** Python + obs-websocket
```python
# tools/obs_controller.py
import obsws_python as obs

client = obs.ReqClient(host='localhost', port=4455, password='your_password')

def switch_scene(scene_name):
    """Переключить сцену"""
    client.set_current_program_scene(scene_name)

def update_text(source_name, text):
    """Обновить текст на оверлее"""
    client.set_input_settings(
        input_name=source_name,
        input_settings={"text": text}
    )

def start_stream():
    client.start_stream()

def stop_stream():
    client.stop_stream()

def update_market_overlay(market_data):
    """Обновить данные рынков на оверлее стрима"""
    for i, market in enumerate(market_data[:5]):
        update_text(f"market_{i}_name", market['question'])
        update_text(f"market_{i}_price", f"Yes: ${market['yes_price']}")
```

**Сценарий стрима с Claude:**
```
ПЕРЕД стримом:
1. Claude собирает горячие рынки с Polymarket API
2. Claude обновляет оверлей через OBS Controller
3. Claude генерирует план стрима

ВО ВРЕМЯ стрима (ты ведёшь):
4. Claude по команде переключает сцены
5. Claude обновляет данные рынков в реальном времени
6. Claude мониторит чат (через скрипт) и подсказывает ответы

ПОСЛЕ стрима:
7. Claude берёт запись → нарезает → создаёт Shorts
```

**Стоимость:** Бесплатно (OBS + websocket)
**Сложность:** Средняя

---

### ИНСТРУМЕНТ 6: Telegram Bot (Community)
**Что делает:** Управляет Telegram-каналом, отвечает в чате
**Как Claude использует:** Создаёт посты, отвечает на вопросы подписчиков

**Реализация:** Python + python-telegram-bot
```python
# tools/telegram_bot.py
from telegram import Bot
import asyncio

bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def send_message(chat_id, text, parse_mode="HTML"):
    """Отправить сообщение в канал/чат"""
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode
    )

async def send_daily_markets(markets):
    """Ежедневная рассылка горячих рынков"""
    text = "<b>🔥 Hot Markets Today</b>\n\n"
    for m in markets[:5]:
        text += f"• {m['question']}\n"
        text += f"  Yes: ${m['yes_price']} | Vol: ${m['volume']}\n\n"
    text += '<a href="https://yoursite.com/polymarket/promo-code.html">Start trading →</a>'
    await send_message(CHANNEL_ID, text)
```

**Claude ежедневно:**
```
1. Собирает данные с Polymarket API
2. Форматирует сообщение
3. Вызывает send_daily_markets()
4. Канал получает пост с горячими рынками + реф ссылка
```

**Стоимость:** Бесплатно
**Сложность:** Низкая

---

### ИНСТРУМЕНТ 7: Деплой сайта
**Что делает:** Деплоит изменения на хостинг
**Как Claude использует:** После обновления контента → пуш → деплой

**Реализация:** Git + Cloudflare Pages / Netlify
```bash
# tools/deploy.sh
cd /path/to/site
git add -A
git commit -m "Content update $(date +%Y-%m-%d)"
git push origin main
# Cloudflare Pages автоматически деплоит после push
echo "Deployed successfully"
```

**Claude после обновления контента:**
```
1. Обновляет файлы сайта
2. Вызывает deploy.sh
3. Сайт обновлён через 30 секунд
```

**Стоимость:** Бесплатно (Cloudflare Pages)
**Сложность:** Низкая

---

### ИНСТРУМЕНТ 8: Скриншотер (для SEO-мониторинга)
**Что делает:** Делает скриншоты поисковой выдачи
**Как Claude использует:** "Загугли X, скриншотни, сохрани"

**Реализация:** Python + Playwright
```python
# tools/serp_screenshot.py
from playwright.sync_api import sync_playwright
import sys, os
from datetime import date

def screenshot_serp(query, output_dir="reports/serp"):
    os.makedirs(output_dir, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"https://www.google.com/search?q={query}&gl=us&hl=en")
        page.wait_for_timeout(2000)
        filename = f"{output_dir}/{date.today()}_{query[:40]}.png"
        page.screenshot(path=filename, full_page=True)
        browser.close()
    return filename

if __name__ == '__main__':
    query = sys.argv[1]
    path = screenshot_serp(query)
    print(f"Screenshot saved: {path}")
```

**Стоимость:** Бесплатно
**Сложность:** Низкая

---

## СОБИРАЕМ ВСЁ ВМЕСТЕ: ДНЕВНОЙ ЦИКЛ

```
06:00  [Scheduled] Polymarket API → собрать горячие рынки
06:05  [Scheduled] Подготовить пост для Twitter
06:10  [Scheduled] Опубликовать в Telegram канал
09:00  [Scheduled] SEO-монитор → проверить позиции в GSC
09:15  [Auto] Если позиции упали → Claude анализирует и предлагает фикс
10:00  [Dispatch] Ты: "обнови контент на сайте"
10:01  [Claude] Проверяет Polymarket → обновляет HTML → деплоит
12:00  [Scheduled] Trading bot → проверить позиции, отчёт
14:00  [Dispatch] Ты: "подготовь материал для видео"
14:01  [Claude] Пишет скрипт → ElevenLabs озвучка → собирает видео
17:00  [Scheduled] Скриншот SERP → мониторинг конкурентов
18:00  [Scheduled] Сводный отчёт за день → отправить в Telegram тебе
```

---

## ЧТО НУЖНО КУПИТЬ / НАСТРОИТЬ (полный список)

### Этап 1: Базовый (неделя 1) — $35/мес
| Компонент | Что | Цена |
|-----------|-----|------|
| Claude Pro | Cowork + Dispatch | $20/мес |
| Домен | predicthub.com или аналог | ~$12/год |
| Cloudflare Pages | Хостинг | Бесплатно |
| Git (GitHub) | Версионирование | Бесплатно |
| Google Search Console | SEO-мониторинг | Бесплатно |
| Telegram Bot | Community канал | Бесплатно |
| Python 3.11+ | Скрипты | Бесплатно |

### Этап 2: Контент-машина (неделя 3) — +$27/мес
| Компонент | Что | Цена |
|-----------|-----|------|
| X/Twitter API | Автопостинг | Бесплатно (Free tier) |
| ElevenLabs Starter | AI-озвучка | $5/мес |
| Canva Pro | Графика | $13/мес |
| YouTube API | Загрузка видео | Бесплатно |
| MoviePy + Playwright | Видео + скриншоты | Бесплатно |

### Этап 3: Торговля (неделя 5) — +$5-20/мес
| Компонент | Что | Цена |
|-----------|-----|------|
| VPS (DigitalOcean) | Бот 24/7 | $5-20/мес |
| Polymarket API | Торговый доступ | Бесплатно |
| Капитал | Для торговли | $500-5000 (разовое) |
| py-clob-client | Python SDK | Бесплатно |

### Этап 4: Масштаб (месяц 2+) — +$100-230/мес
| Компонент | Что | Цена |
|-----------|-----|------|
| Claude Max | Больше лимитов | +$80 (апгрейд с Pro) |
| Ahrefs Lite | SEO-аналитика конкурентов | $129/мес |
| ElevenLabs Creator | Больше озвучки | +$17 (апгрейд) |
| OBS + StreamYard | Стримы | Бесплатно / $20/мес |

---

## ПОРЯДОК СОЗДАНИЯ ИНСТРУМЕНТОВ

| # | Инструмент | Приоритет | Время создания | Импакт |
|---|-----------|-----------|---------------|--------|
| 1 | Deploy скрипт (git push) | P0 | 10 мин | Сайт обновляется |
| 2 | Twitter автопостер | P0 | 30 мин | Виральный трафик → SEO буст |
| 3 | Telegram бот | P1 | 1 час | Community → RevShare |
| 4 | SERP скриншотер | P1 | 30 мин | Мониторинг позиций |
| 5 | GSC MCP-сервер | P1 | 1 час | SEO-аналитика |
| 6 | Polymarket API скрипты | P2 | 2 часа | Данные для контента + торговля |
| 7 | Видео-генератор | P2 | 3 часа | YouTube контент |
| 8 | OBS контроллер | P3 | 2 часа | Стримы |
| 9 | Trading bot | P3 | 4 часа | Доход от торговли |
