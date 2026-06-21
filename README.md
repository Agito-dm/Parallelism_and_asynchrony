# Parallelism and Asynchrony

Проект реализует асинхронный web crawler по дням:
- Day 1 — асинхронная загрузка страниц через `aiohttp`
- Day 2 — парсинг HTML и извлечение данных через `BeautifulSoup`
- Day 3 — очередь URL, управление конкурентностью, глубина обхода и фильтрация ссылок
- Day 4 — rate limiting, robots.txt, crawl-delay, User-Agent, jitter, exponential backoff и мониторинг скорости
- Day 5 — классификация ошибок, RetryStrategy, автоматические повторы, HTTP-статусы, таймауты, логирование и статистика ошибок
- Day 6 — асинхронное сохранение данных в JSONL, CSV и SQLite, единый storage-интерфейс, batch-запись и обработка ошибок сохранения



## Структура проекта

```text
src/
  crawler_day1/
    crawler.py
    demo.py

  crawler_day2/
    crawler.py
    html_parser.py
    demo.py

  crawler_day3/
    crawler.py
    crawler_queue.py
    semaphore_manager.py
    demo.py
  
  crawler_day4/
    crawler.py
    rate_limiter.py
    robots_parser.py
    demo.py
  
  crawler_day5/
    __init__.py
    crawler.py
    errors.py
    retry_strategy.py
    demo.py
  
  crawler_day6/
    __init__.py
    crawler.py
    storage.py
    demo.py

tests/
  day1/
  day2/
  day3/
  day4/
  day5/
  day6/

data/
  day3_results.json
  day5_error_report.json
```



## Установка и запуск


### 1. Клонирование проекта

```bash
git clone <repository-url>
cd Parallelism_and_asynchrony
```

### 2. Создание и активация виртуального окружения

Windows PowerShell:

python -m venv .venv
.\.venv\Scripts\activate

Если PowerShell блокирует активацию:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\activate

Также можно активировать через .bat:

.\.venv\Scripts\activate.bat

### 3. Установка зависимостей
pip install -r requirements.txt

### 4. Запуск тестов

Все тесты проекта:

pytest -v

Тесты отдельного дня:

pytest tests/day6 -v

### 5. Запуск demo

Примеры запуска demo-модулей:

python -m crawler_day5.demo
python -m crawler_day6.demo

Demo шестого дня сохраняет результаты в:

data/day6_demo/results.jsonl
data/day6_demo/results.csv
data/day6_demo/crawler.db
