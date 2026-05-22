"""P33 schema tests.

Covers TS01 (smoke), TS02 (coverage), TS03 (partial regression),
TS07 (provider fields), TS08 (mode/profile prompt surface).

Strict-mode validation uses ConfigSchema.validate(..., strict=True).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


def _walk_leaves(d: dict[str, Any], prefix: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    """Yield every leaf path through a nested dict.

    A "leaf" is a path whose value is NOT a dict. Empty dicts (e.g.
    `modes = {}`) are considered leaves themselves.
    """
    out: list[tuple[str, ...]] = []
    for key, value in d.items():
        path = prefix + (key,)
        if isinstance(value, dict) and value:
            out.extend(_walk_leaves(value, path))
        else:
            out.append(path)
    return out


# ---------- TS01: smoke ----------


def test_doxa_config_constructs_with_no_overrides() -> None:
    from doxa_research.config_schema import DoxaConfig

    cfg = DoxaConfig()
    assert cfg.version == "2.0"


def test_get_defaults_equals_root_schema_dump() -> None:
    from doxa_research.config import ConfigSchema
    from doxa_research.config_schema import default_config_dict

    assert ConfigSchema.get_defaults() == default_config_dict()


def test_get_defaults_recomputes_checkpoint_dir_after_xdg_state_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from doxa_research.config import ConfigSchema

    # Force the schema module to import and compute any cached defaults before
    # changing the environment. Runtime defaults must still reflect the active
    # environment when requested later.
    ConfigSchema.get_defaults()
    state_home = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))

    defaults = ConfigSchema.get_defaults()

    assert defaults["paths"]["checkpoint_dir"] == str(state_home / "doxa" / "checkpoints")


# ---------- TS02: coverage (default paths only at this stage) ----------


def test_every_default_path_resolves_to_a_field() -> None:
    """Every leaf path in get_defaults() must resolve to a DoxaConfig field.

    This is the test that catches the `prompy_prefix` typo class.
    """
    from doxa_research.config import ConfigSchema
    from doxa_research.config_schema import DoxaConfig, resolve_path

    defaults = ConfigSchema.get_defaults()
    for path in _walk_leaves(defaults):
        # `resolve_path` returns a (model, field_name) tuple or raises
        # KeyError if the path doesn't reach a declared field.
        resolve_path(DoxaConfig, path)


def test_resolve_path_recurses_into_dict_of_basemodel() -> None:
    """`modes: dict[str, ModeConfig]` — paths past the dict key recurse into ModeConfig."""
    from doxa_research.config_schema import DoxaConfig, ModeConfig, resolve_path

    model, name = resolve_path(DoxaConfig, ("modes", "thinking", "provider"))
    assert model is ModeConfig
    assert name == "provider"


def test_resolve_path_providers_recurses_into_openai_config() -> None:
    """`providers: ProvidersConfig` — value type is a BaseModel (Task 4),
    so resolve_path recurses into OpenAIConfig and resolves the leaf field.
    """
    from doxa_research.config_schema import DoxaConfig, OpenAIConfig, resolve_path

    model, name = resolve_path(DoxaConfig, ("providers", "openai", "api_key"))
    assert model is OpenAIConfig
    assert name == "api_key"


def test_resolve_path_raises_on_unknown_leaf() -> None:
    """Typos like `general.prompy_prefix` must raise KeyError — this is the
    very behavior P33 exists to guarantee."""
    from doxa_research.config_schema import DoxaConfig, resolve_path

    with pytest.raises(KeyError):
        resolve_path(DoxaConfig, ("general", "prompy_prefix"))


# ---------- TS03: make_partial regression ----------


def test_make_partial_keeps_field_set() -> None:
    """make_partial(DoxaConfig) must produce a model with the same field
    set as DoxaConfig, all marked optional with `None` defaults."""
    from doxa_research.config_schema import DoxaConfig, PartialDoxaConfig

    src_fields = set(DoxaConfig.model_fields.keys())
    partial_fields = set(PartialDoxaConfig.model_fields.keys())
    assert src_fields == partial_fields, (
        f"PartialDoxaConfig field set drifted from DoxaConfig: "
        f"missing {src_fields - partial_fields}, extra {partial_fields - src_fields}"
    )

    for name, finfo in PartialDoxaConfig.model_fields.items():
        # Each field must have a `None` default, signalling "unset = ok"
        assert finfo.default is None and finfo.default_factory is None, (
            f"PartialDoxaConfig.{name} should default to None with no factory; "
            f"got default={finfo.default!r}, factory={finfo.default_factory!r}"
        )


def test_make_partial_constructs_empty() -> None:
    from doxa_research.config_schema import PartialDoxaConfig

    PartialDoxaConfig()  # must not raise


# ---------- TS02: overlay-path coverage ----------


def test_user_only_overlay_paths_resolve() -> None:
    """Valid P21 user-only fields must resolve through ConfigOverlay /
    ProfileConfig, even though they are NOT part of get_defaults()."""
    from doxa_research.config_schema import ConfigOverlay, ProfileConfig, resolve_path

    resolve_path(ConfigOverlay, ("general", "default_profile"))
    resolve_path(ConfigOverlay, ("general", "prompt_prefix"))
    resolve_path(ConfigOverlay, ("modes", "thinking", "system_prompt"))
    resolve_path(ConfigOverlay, ("modes", "thinking", "prompt_prefix"))
    resolve_path(ProfileConfig, ("prompt_prefix",))


# ---------- TS08: mode/profile prompt surface validates ----------


def test_mode_table_with_prompts_validates() -> None:
    from doxa_research.config_schema import ModeConfig

    ModeConfig(system_prompt="Be precise", prompt_prefix="Cite sources")


def test_profile_with_root_and_nested_prompts_validates() -> None:
    from doxa_research.config_schema import ModeConfig, ProfileConfig

    profile = ProfileConfig(
        prompt_prefix="Be thorough",
        modes={"thinking": ModeConfig(system_prompt="Step by step")},
    )
    assert profile.prompt_prefix == "Be thorough"
    assert profile.modes is not None and "thinking" in profile.modes


def test_user_file_with_full_p21_shape_validates() -> None:
    from doxa_research.config_schema import UserConfigFile

    doc = {
        "general": {
            "default_project": "daily-notes",
            "default_profile": "fast",
            "prompt_prefix": "Cite sources",
        },
        "modes": {"thinking": {"system_prompt": "Be careful"}},
        "profiles": {
            "fast": {
                "prompt_prefix": "Be quick",
                "modes": {"thinking": {"system_prompt": "Profile prompt"}},
            }
        },
    }
    UserConfigFile.model_validate(doc)


def test_typo_at_each_overlay_level_raises() -> None:
    from pydantic import ValidationError

    from doxa_research.config_schema import ProfileConfig, UserConfigFile

    with pytest.raises(ValidationError):
        UserConfigFile.model_validate({"general": {"prompy_prefix": "x"}})

    with pytest.raises(ValidationError):
        ProfileConfig.model_validate({"prompy_prefix": "x"})

    with pytest.raises(ValidationError):
        UserConfigFile.model_validate(
            {"profiles": {"fast": {"modes": {"thinking": {"system_prompy": "x"}}}}}
        )


def test_general_overlay_mirrors_general_config_fields() -> None:
    from doxa_research.config_schema import GeneralConfig, GeneralOverlay

    runtime = set(GeneralConfig.model_fields.keys())
    overlay = set(GeneralOverlay.model_fields.keys())
    missing = runtime - overlay
    assert not missing, (
        f"GeneralOverlay is missing fields present in GeneralConfig: {missing}. "
        f"Add them as `<name>: T | None = None` to GeneralOverlay."
    )
    overlay_only = overlay - runtime
    assert overlay_only == {"default_profile", "prompt_prefix"}, (
        f"Unexpected overlay-only fields: {overlay_only}. "
        f"Update this test if you intentionally added a new P21-style field."
    )


# ---------- TS07: provider-specific schema fields ----------


def test_openai_provider_temperature_validates() -> None:
    from doxa_research.config_schema import OpenAIConfig

    OpenAIConfig(api_key="${OPENAI_API_KEY}", temperature=0.7)


def test_perplexity_nested_namespace_validates() -> None:
    """Perplexity's runtime forwards the `perplexity` namespace dict to
    `extra_body` — including `web_search_options.search_context_size`,
    `stream_mode`, and any future SDK options. Schema accepts arbitrary
    keys under that namespace for forward-compat.
    """
    from doxa_research.config_schema import PerplexityConfig

    PerplexityConfig(
        api_key="${PERPLEXITY_API_KEY}",
        perplexity={
            "stream_mode": "full",
            "web_search_options": {"search_context_size": "high"},
        },
    )


def test_perplexity_direct_sdk_keys_validate() -> None:
    """Top-level direct SDK keys (per `_DIRECT_SDK_KEYS` in
    `src/doxa_research/providers/perplexity.py`): top_p, stop, response_format,
    plus inherited temperature/max_tokens.
    """
    from doxa_research.config_schema import PerplexityConfig

    PerplexityConfig(
        api_key="${PERPLEXITY_API_KEY}",
        temperature=0.5,
        max_tokens=2000,
        top_p=0.9,
        stop=["END"],
        response_format={"type": "json_object"},
    )


def test_openai_advanced_runtime_fields_validate() -> None:
    """OpenAI's runtime reads max_tool_calls, code_interpreter, background,
    organization. All must pass schema validation since the runtime expects
    them on `provider_config`.
    """
    from doxa_research.config_schema import OpenAIConfig

    OpenAIConfig(
        api_key="${OPENAI_API_KEY}",
        organization="org-test",
        max_tool_calls=50,
        code_interpreter=False,
        background=True,
    )


def test_unknown_openai_field_rejected() -> None:
    from pydantic import ValidationError

    from doxa_research.config_schema import OpenAIConfig

    with pytest.raises(ValidationError) as exc:
        OpenAIConfig(api_key="${OPENAI_API_KEY}", bogus=1)  # type: ignore[call-arg]  # ty: ignore[unknown-argument]
    assert "bogus" in str(exc.value)


def test_perplexity_rejects_openai_specific_fields() -> None:
    from pydantic import ValidationError

    from doxa_research.config_schema import PerplexityConfig

    # `organization` is OpenAI-specific; Perplexity must reject it.
    with pytest.raises(ValidationError) as exc:
        PerplexityConfig(api_key="${PERPLEXITY_API_KEY}", organization="acme")  # type: ignore[call-arg]  # ty: ignore[unknown-argument]
    assert "organization" in str(exc.value)


def test_providers_config_holds_typed_subsections() -> None:
    from doxa_research.config_schema import ProvidersConfig

    p = ProvidersConfig()
    assert p.openai.api_key == "${OPENAI_API_KEY}"
    assert p.perplexity.api_key == "${PERPLEXITY_API_KEY}"


# ---------- starter_keys() coverage ----------


def test_starter_keys_includes_top_level_in_starter_leaves() -> None:
    """Every leaf decorated with StarterField shows up in starter_keys()."""
    from doxa_research.config_schema import ConfigSchema

    keys = ConfigSchema.starter_keys()
    # Expected leaves shipped by `doxa init` per the field declarations:
    expected_some = {
        ("general", "default_project"),
        ("general", "default_mode"),
        ("paths", "base_output_dir"),
        ("paths", "checkpoint_dir"),
        ("execution", "poll_interval"),
        ("execution", "max_wait"),
        ("execution", "parallel_providers"),
        ("execution", "retry_attempts"),
        ("execution", "auto_input"),
        ("output", "combine_reports"),
        ("output", "format"),
        ("output", "include_metadata"),
        ("output", "timestamp_format"),
    }
    missing = expected_some - keys
    assert not missing, f"starter_keys() missing expected leaves: {missing}. Got: {sorted(keys)}"


def test_starter_keys_excludes_advanced_execution_fields() -> None:
    """`max_transient_errors`, `prompt_max_bytes`, `cancel_upstream_on_interrupt`
    are deliberately NOT in starter."""
    from doxa_research.config_schema import ConfigSchema

    keys = ConfigSchema.starter_keys()
    forbidden = {
        ("execution", "max_transient_errors"),
        ("execution", "prompt_max_bytes"),
        ("execution", "cancel_upstream_on_interrupt"),
    }
    leaked = forbidden & keys
    assert not leaked, f"Advanced fields leaked into starter_keys(): {leaked}"


def test_gemini_config_has_dr_tunables() -> None:
    """Task 11: GeminiConfig exposes Deep Research polling tunables."""
    from doxa_research.config_schema import GeminiConfig

    cfg = GeminiConfig(api_key="test-key")
    assert hasattr(cfg, "poll_interval")
    assert cfg.poll_interval == 10  # default 10s
    assert hasattr(cfg, "max_wait_minutes")
    assert cfg.max_wait_minutes == 60  # upstream max research time


def test_starter_keys_includes_clarification_section() -> None:
    """The whole `clarification` section is shipped (all 16 leaves are StarterField)."""
    from doxa_research.config_schema import ConfigSchema

    keys = ConfigSchema.starter_keys()
    clarification_keys = {k for k in keys if k and k[0] == "clarification"}
    assert clarification_keys, "Clarification section is missing from starter keys"
    assert len(clarification_keys) == 16, (
        f"Expected 16 clarification keys, got {len(clarification_keys)}: {clarification_keys}"
    )
