from crawler_day7.performance import build_parser, run_benchmark


def test_day7_performance_parser_accepts_arguments():
    parser = build_parser()

    args = parser.parse_args(
        [
            "--pages",
            "10",
            "--max-concurrent",
            "5",
            "--delay",
            "0.01",
            "--json-output",
            "data/benchmark.json",
        ]
    )

    assert args.pages == 10
    assert args.max_concurrent == 5
    assert args.delay == 0.01
    assert args.json_output == "data/benchmark.json"


async def test_day7_run_benchmark_returns_performance_metrics():
    result = await run_benchmark(
        page_count=5,
        max_concurrent=2,
        delay=0.0,
    )

    assert result["page_count"] == 5
    assert result["max_concurrent"] == 2
    assert result["async_duration_seconds"] >= 0
    assert result["async_pages_per_second"] >= 0
    assert result["sync_duration_seconds"] >= 0
    assert result["sync_pages_per_second"] >= 0
    assert result["peak_memory_kb"] >= 0
    assert "speedup_vs_sync" in result
