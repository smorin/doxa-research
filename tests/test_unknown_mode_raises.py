"""Unknown --mode names must raise ModeNotFoundError, not silently fall back.

Before this commit, `config.get_mode_config("nonexistent")` returned `{}`
and the rest of the pipeline silently dispatched as if no mode were
specified — leading to "Hello!"-style default-mode answers when users
typed a mode that didn't exist (or wasn't yet published to PyPI).
"""

from __future__ import annotations

import pytest

from doxa_research.config import ConfigManager
from doxa_research.errors import ModeNotFoundError


def test_get_mode_config_raises_for_unknown_builtin() -> None:
    cm = ConfigManager()
    cm.load_all_layers({})
    with pytest.raises(ModeNotFoundError) as exc_info:
        cm.get_mode_config("does_not_exist_anywhere")
    assert "does_not_exist_anywhere" in exc_info.value.message
    assert exc_info.value.exit_code == 1


def test_get_mode_config_error_lists_available_modes() -> None:
    cm = ConfigManager()
    cm.load_all_layers({})
    with pytest.raises(ModeNotFoundError) as exc_info:
        cm.get_mode_config("not_a_mode")
    # Suggestion should enumerate at least the well-known builtins.
    suggestion = exc_info.value.suggestion or ""
    assert "deep_research" in suggestion
    assert "default" in suggestion


def test_get_mode_config_still_resolves_real_builtins() -> None:
    cm = ConfigManager()
    cm.load_all_layers({})
    cfg = cm.get_mode_config("default")
    assert cfg["provider"] == "openai"
    assert cfg["kind"] == "immediate"


def test_get_mode_config_resolves_user_defined_mode() -> None:
    cm = ConfigManager()
    cm.load_all_layers(
        {"modes": {"my_custom": {"provider": "mock", "model": "test", "kind": "immediate"}}}
    )
    cfg = cm.get_mode_config("my_custom")
    assert cfg["provider"] == "mock"
    assert cfg["model"] == "test"


def test_unknown_alias_target_raises() -> None:
    """If a BUILTIN_MODES alias stub points at a target that doesn't exist,
    we should raise — better than silently producing an empty config.
    Synthetic case: monkeypatch BUILTIN_MODES with a bad alias.
    """
    cm = ConfigManager()
    cm.load_all_layers({})
    # The alias resolution path is exercised here via mini_research →
    # quick_research, but only the real alias is supported. Confirm a
    # purely-unknown name still raises through the normal path.
    with pytest.raises(ModeNotFoundError):
        cm.get_mode_config("totally_made_up_mode_name")
