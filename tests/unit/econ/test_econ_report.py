from adaptiverag.telemetry.aggregate import quality_per_cost, selector, summarize
from bench.econ import markdown
from tests.unit.econ.test_aggregate import ROWS


def report(floor: float) -> str:
    s = summarize(ROWS)
    e = {
        **s,
        "quality_per_cost": quality_per_cost(s["runs"], floor),
        "selector": selector(ROWS, "m"),
        "faithfulness_floor": floor,
    }
    return markdown("20260930-0900-dev", e)


def test_report_renders_every_table_with_run_ids() -> None:
    md = report(0.6)
    for heading in (
        "## Runs",
        "## Cost per query type",
        "## Cost per route",
        "## Quality per unit cost",
    ):
        assert heading in md
    assert "## Model selector" in md and "`r1`" in md and "judge.flag_below" in md


def test_eligibility_follows_the_floor() -> None:
    # the fixture run's mean faithfulness is 0.65
    assert "| yes |" in report(0.6)
    assert "no (faithfulness under 0.7)" in report(0.7)
