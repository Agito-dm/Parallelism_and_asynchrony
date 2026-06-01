# Parallelism and Asynchrony

Проект реализует асинхронный web crawler по дням:
- Day 1 — асинхронная загрузка страниц через `aiohttp`
- Day 2 — парсинг HTML и извлечение данных через `BeautifulSoup`
- Day 3 — очередь URL, управление конкурентностью, глубина обхода и фильтрация ссылок



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

tests/
  test_crawler.py
  test_day2_parser.py
  test_day3_queue.py
  test_day3_semaphore.py
  test_day3_crawler.py

data/
  day3_results.json
```