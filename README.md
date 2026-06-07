# Parallelism and Asynchrony

Проект реализует асинхронный web crawler по дням:
- Day 1 — асинхронная загрузка страниц через `aiohttp`
- Day 2 — парсинг HTML и извлечение данных через `BeautifulSoup`
- Day 3 — очередь URL, управление конкурентностью, глубина обхода и фильтрация ссылок
- Day 4 — rate limiting, robots.txt, crawl-delay, User-Agent, jitter, exponential backoff и мониторинг скорости
- Day 5 — классификация ошибок, RetryStrategy, автоматические повторы, HTTP-статусы, таймауты, логирование и статистика ошибок



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

tests/
  day1/
  day2/
  day3/
  day4/
  day5/

data/
  day3_results.json
  day5_error_report.json
```