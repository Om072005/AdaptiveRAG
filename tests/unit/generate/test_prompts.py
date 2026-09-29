from pathlib import Path

from adaptiverag.generate.prompts import build_prompt

from .fixtures import retrieved

SNAPSHOT = Path(__file__).parent / "snapshots" / "prompt.txt"


def render(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(f"### {m['role']}\n{m['content']}" for m in messages) + "\n"


def test_prompt_matches_snapshot() -> None:
    text = render(
        build_prompt(
            "What is the capital of the country whose largest city is Istanbul?", retrieved()
        )
    )
    if not SNAPSHOT.exists():  # first run writes it; review the file before committing
        SNAPSHOT.write_text(text, encoding="utf-8", newline="\n")
    assert text == SNAPSHOT.read_text(encoding="utf-8")


def test_blocks_follow_hit_rank_not_list_order() -> None:
    user = build_prompt("q", retrieved())[1]["content"]
    assert user.index("[1] Istanbul") < user.index("[2] Ankara")
