"""Settings from the environment and the three config files in config/."""

import hashlib
import os
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, cast, get_args

from adaptiverag.types import Role

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
CONFIG_FILES = ("models.toml", "router.toml", "ingest.toml")
PLACEHOLDER = "PIN_ME"


class ConfigError(Exception):
    """A config file or setting is missing, malformed or still has a placeholder."""


@dataclass(frozen=True)
class Settings:
    database_url: str
    database_url_direct: str
    gemini_api_key: str
    allow_test: bool
    live_daily_budget_usd: float
    live_rate_limit_per_10min: int
    ip_hash_salt: str


@dataclass(frozen=True)
class ModelSpec:
    role: Role
    provider: str
    model: str
    base_url: str
    key_env: str
    price_in_per_m: float
    price_out_per_m: float
    reasoning_effort: str | None
    dims: int | None
    server_error_attempts: int = 5  # attempts on 5xx; 1 = never retry a busy provider
    texts_per_minute: int | None = None  # embeddings: paced under the provider's per minute cap
    document_prefix: str = ""  # embeddings: prepended to texts that are searched
    query_prefix: str = ""  # embeddings: prepended to questions


def parse_env(text: str) -> dict[str, str]:
    """Parse KEY=VALUE lines of a .env file, skipping comments and trailing ' # notes'."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.split(" #", 1)[0].strip().strip("\"'")
        values[key.strip()] = value
    return values


def settings() -> Settings:
    """Environment variables, falling back to the repo .env file. Real env always wins."""
    env_file = ROOT / ".env"
    env = parse_env(env_file.read_text(encoding="utf-8")) if env_file.exists() else {}
    env.update({k: v for k, v in os.environ.items() if v})

    def get(key: str, default: str = "") -> str:
        return env.get(key, default)

    return Settings(
        database_url=get("DATABASE_URL"),
        database_url_direct=get("DATABASE_URL_DIRECT"),
        gemini_api_key=get("GEMINI_API_KEY"),
        allow_test=get("ALLOW_TEST", "0") == "1",
        live_daily_budget_usd=float(get("LIVE_DAILY_BUDGET_USD", "0.25")),
        live_rate_limit_per_10min=int(get("LIVE_RATE_LIMIT_PER_10MIN", "10")),
        ip_hash_salt=get("IP_HASH_SALT"),
    )


def find_placeholders(value: Any, path: str = "") -> list[str]:
    """Dotted paths of every value that still contains the PIN_ME placeholder."""
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in find_placeholders(v, f"{path}.{k}".strip("."))]
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in find_placeholders(v, f"{path}[{i}]")]
    return [path] if isinstance(value, str) and PLACEHOLDER in value else []


def read_toml(name: str, config_dir: Path = CONFIG_DIR) -> dict[str, Any]:
    """Load one config file and refuse it while any value is still a placeholder."""
    data = tomllib.loads((config_dir / name).read_text(encoding="utf-8"))
    pinned = find_placeholders(data)
    if pinned:
        raise ConfigError(f"{name} still has {PLACEHOLDER} at: {', '.join(pinned)}")
    return data


def parse_models(data: dict[str, Any]) -> dict[Role, ModelSpec]:
    """Build one ModelSpec per role from the parsed models.toml; every role must be present."""
    providers, roles = data.get("providers", {}), data.get("roles", {})
    missing = [r for r in get_args(Role) if r not in roles]
    if missing:
        raise ConfigError(f"models.toml has no role: {', '.join(missing)}")
    specs: dict[Role, ModelSpec] = {}
    for name, spec in roles.items():
        if name not in get_args(Role):
            raise ConfigError(f"models.toml has an unknown role: {name}")
        provider = providers.get(spec["provider"])
        if provider is None:
            raise ConfigError(f"role {name} uses unknown provider {spec['provider']}")
        role = cast(Role, name)
        specs[role] = ModelSpec(
            role=role,
            provider=spec["provider"],
            model=spec["model"],
            base_url=provider["base_url"],
            key_env=provider["key_env"],
            price_in_per_m=float(spec["price_in_per_m"]),
            price_out_per_m=float(spec.get("price_out_per_m", 0.0)),
            reasoning_effort=spec.get("reasoning_effort"),
            dims=spec.get("dims"),
            server_error_attempts=int(spec.get("server_error_attempts", 5)),
            texts_per_minute=spec.get("texts_per_minute"),
            document_prefix=str(spec.get("document_prefix", "")),
            query_prefix=str(spec.get("query_prefix", "")),
        )
    return specs


@cache
def models() -> dict[Role, ModelSpec]:
    """Model id, provider and list price per role, from config/models.toml."""
    return parse_models(read_toml("models.toml"))


@cache
def limits() -> dict[str, Any]:
    """The [limits] table of config/models.toml (per query call cap)."""
    return dict(read_toml("models.toml").get("limits", {}))


@cache
def router_cfg() -> dict[str, Any]:
    """Thresholds from config/router.toml."""
    return read_toml("router.toml")


@cache
def ingest_cfg() -> dict[str, Any]:
    """Chunking, extraction and resolution settings from config/ingest.toml."""
    return read_toml("ingest.toml")


def config_hash(config_dir: Path = CONFIG_DIR) -> str:
    """First 12 hex of sha256 over the three config files, line endings normalized."""
    digest = hashlib.sha256()
    for name in CONFIG_FILES:
        digest.update((config_dir / name).read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()[:12]
