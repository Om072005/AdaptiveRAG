import shutil
from pathlib import Path

import pytest

from adaptiverag import config
from adaptiverag.config import ConfigError


def test_all_three_files_load() -> None:
    specs = config.models()
    assert set(specs) == {"small", "large", "extract", "judge", "classify", "embed"}
    assert specs["large"].provider == "ollama"
    assert specs["judge"].provider == "ollama"  # D21
    assert specs["embed"].dims == 768
    assert config.limits()["max_llm_calls_per_query"] == 4
    assert config.router_cfg()["serving"]["chunk_strategy"] in {"fixed", "sentence", "semantic"}
    assert config.ingest_cfg()["chunk"]["fixed"]["n_words"] > 0


def test_judge_is_a_different_family_from_the_generators() -> None:
    # every model is served by Ollama since D21, so the family is read from the model name
    specs = config.models()

    def family(model: str) -> str:
        return model.split(":")[0].split("-")[0].rstrip("0123456789.")

    judge = family(specs["judge"].model)
    assert judge not in {family(specs[r].model) for r in ("small", "large", "classify", "extract")}


def test_placeholder_anywhere_raises(tmp_path: Path) -> None:
    for name in config.CONFIG_FILES:
        shutil.copy(config.CONFIG_DIR / name, tmp_path / name)
    text = (tmp_path / "models.toml").read_text(encoding="utf-8")
    (tmp_path / "models.toml").write_text(text.replace("0.018", '"PIN_ME"', 1), encoding="utf-8")
    with pytest.raises(ConfigError, match="roles.small.price_in_per_m"):
        config.read_toml("models.toml", tmp_path)


def test_missing_role_raises() -> None:
    data = {"providers": {"ollama": {"base_url": "u", "key_env": ""}}, "roles": {}}
    with pytest.raises(ConfigError, match="no role"):
        config.parse_models(data)


def test_parse_env_ignores_comments_and_quotes() -> None:
    text = '# c\nDATABASE_URL="postgres://x"\nALLOW_TEST=0   # note\n\nBAD LINE\nEMPTY=\n'
    assert config.parse_env(text) == {
        "DATABASE_URL": "postgres://x",
        "ALLOW_TEST": "0",
        "EMPTY": "",
    }


def test_config_hash_ignores_line_endings(tmp_path: Path) -> None:
    for name in config.CONFIG_FILES:
        data = (config.CONFIG_DIR / name).read_bytes().replace(b"\r\n", b"\n")
        (tmp_path / name).write_bytes(data.replace(b"\n", b"\r\n"))
    assert config.config_hash(tmp_path) == config.config_hash()
    assert len(config.config_hash()) == 12


def test_settings_prefers_real_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_TEST", "1")
    monkeypatch.setenv("DATABASE_URL", "postgres://from-env")
    s = config.settings()
    assert s.allow_test is True
    assert s.database_url == "postgres://from-env"


def test_json_mode_defaults_on_and_a_role_can_turn_it_off() -> None:
    data = config.read_toml("models.toml")
    assert all(s.json_mode for r, s in config.parse_models(data).items() if r != "judge")
    data["roles"]["judge"]["json_mode"] = False
    assert config.parse_models(data)["judge"].json_mode is False
