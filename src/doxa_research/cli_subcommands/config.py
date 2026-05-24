"""`doxa config` Click subgroup with leaves: get, set, unset, list, path, edit."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NoReturn

import click

from doxa_research.cli_subcommands._option_policy import (
    DEFAULT_HONOR,
    NO_INHERITED_OPTIONS,
    inherited_value,
    validate_inherited_options,
)
from doxa_research.completion.sources import config_keys as _config_keys_completer
from doxa_research.errors import ConfigProfileError, DoxaError
from doxa_research.json_output import emit_doxa_error, emit_error

_PASSTHROUGH_CONTEXT = {"ignore_unknown_options": True, "allow_extra_args": True}
_VALID_LAYERS = ("defaults", "user", "project", "profile", "env", "cli")


def _emit_doxa_error_for_output_mode(
    ctx: click.Context,
    exc: DoxaError,
    *,
    as_json: bool,
) -> NoReturn:
    if as_json:
        emit_doxa_error(exc)
    click.echo(f"Error: {exc.message}", err=True)
    if exc.suggestion:
        click.echo(f"Suggestion: {exc.suggestion}", err=True)
    ctx.exit(exc.exit_code)


@click.group(name="config", invoke_without_command=True)
@click.pass_context
def config(ctx: click.Context) -> None:
    """Inspect and edit configuration."""
    if ctx.invoked_subcommand is None:
        validate_inherited_options(ctx, "config", NO_INHERITED_OPTIONS)
        click.echo(
            "Error: config command requires an op (get|set|unset|list|path|edit|validate|help)",
            err=True,
        )
        ctx.exit(2)


def _dispatch(
    ctx: click.Context,
    op: str,
    args: tuple[str, ...],
    honored_options=DEFAULT_HONOR,
) -> None:
    from doxa_research.config_cmd import config_command
    from doxa_research.errors import ConfigProfileError

    validate_inherited_options(ctx, f"config {op}", honored_options)
    config_path = inherited_value(ctx, "config_path")
    profile = inherited_value(ctx, "profile")
    try:
        rc = config_command(op, list(args), config_path=config_path, profile=profile)
    except ConfigProfileError as exc:
        click.echo(f"Error: {exc.message}")
        if exc.suggestion:
            click.echo(f"Suggestion: {exc.suggestion}")
        sys.exit(exc.exit_code)
    sys.exit(rc)


@config.command(name="get")
@click.argument("key", shell_complete=_config_keys_completer)
@click.option(
    "--layer",
    "layer",
    type=click.Choice(_VALID_LAYERS),
    default=None,
    help="Read from a specific config layer",
)
@click.option(
    "--raw",
    is_flag=True,
    help="Read pre-merge layer data (formatting only; does NOT bypass masking)",
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.option(
    "--show-secrets",
    is_flag=True,
    help="Reveal masked secret values (security-sensitive)",
)
@click.pass_context
def config_get(
    ctx: click.Context,
    key: str,
    layer: str | None,
    raw: bool,
    as_json: bool,
    show_secrets: bool,
) -> None:
    """Get a configuration value."""
    validate_inherited_options(ctx, "config get", DEFAULT_HONOR)
    config_path = inherited_value(ctx, "config_path")

    if as_json:
        from doxa_research.config_cmd import get_config_get_data
        from doxa_research.json_output import emit_json

        profile = inherited_value(ctx, "profile")
        try:
            data = get_config_get_data(
                key,
                layer=layer,
                raw=raw,
                show_secrets=show_secrets,
                config_path=config_path,
                profile=profile,
            )
        except DoxaError as exc:
            emit_doxa_error(exc)
        if data.get("error") == "INVALID_LAYER":
            emit_error(
                "INVALID_LAYER",
                f"--layer must be one of {', '.join(_VALID_LAYERS)}",
                exit_code=2,
            )
        if not data["found"]:
            emit_error("KEY_NOT_FOUND", f"key not found: {key}", {"key": key}, exit_code=1)
        emit_json(data)

    rebuilt: list[str] = [key]
    if layer is not None:
        rebuilt.extend(["--layer", layer])
    if raw:
        rebuilt.append("--raw")
    if show_secrets:
        rebuilt.append("--show-secrets")
    _dispatch(ctx, "get", tuple(rebuilt))


@config.command(name="set", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_set(ctx: click.Context, args: tuple[str, ...], as_json: bool) -> None:
    """Set a configuration value."""
    if as_json:
        from doxa_research.config_cmd import get_config_set_data
        from doxa_research.json_output import emit_error, emit_json

        validate_inherited_options(ctx, "config set", DEFAULT_HONOR)
        config_path = inherited_value(ctx, "config_path")

        positional: list[str] = []
        project = False
        force_string = False
        for a in args:
            if a == "--project":
                project = True
            elif a == "--string":
                force_string = True
            else:
                positional.append(a)

        if len(positional) != 2:
            emit_error("USAGE_ERROR", "config set takes KEY VALUE", exit_code=2)
        key, raw_value = positional[0], positional[1]
        data = get_config_set_data(
            key,
            raw_value,
            project=project,
            force_string=force_string,
            config_path=config_path,
        )
        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    _dispatch(ctx, "set", args)


@config.command(name="unset", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_unset(ctx: click.Context, args: tuple[str, ...], as_json: bool) -> None:
    """Unset a configuration value."""
    if as_json:
        from doxa_research.config_cmd import get_config_unset_data
        from doxa_research.json_output import emit_error, emit_json

        validate_inherited_options(ctx, "config unset", DEFAULT_HONOR)
        config_path = inherited_value(ctx, "config_path")

        positional: list[str] = []
        project = False
        for a in args:
            if a == "--project":
                project = True
            else:
                positional.append(a)

        if len(positional) != 1:
            emit_error("USAGE_ERROR", "config unset takes KEY", exit_code=2)
        key = positional[0]
        data = get_config_unset_data(key, project=project, config_path=config_path)
        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    _dispatch(ctx, "unset", args)


@config.command(name="list", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_list(ctx: click.Context, args: tuple[str, ...], as_json: bool) -> None:
    """List all configuration values. Supports --json."""
    if as_json:
        from doxa_research.config_cmd import get_config_list_data
        from doxa_research.json_output import emit_json

        validate_inherited_options(ctx, "config list", DEFAULT_HONOR)
        config_path = inherited_value(ctx, "config_path")

        layer: str | None = None
        keys_only = False
        show_secrets = False
        i = 0
        rest = list(args)
        while i < len(rest):
            a = rest[i]
            if a == "--layer":
                if i + 1 >= len(rest):
                    emit_error("USAGE_ERROR", "--layer requires a value", exit_code=2)
                layer = rest[i + 1]
                i += 2
            elif a == "--keys":
                keys_only = True
                i += 1
            elif a == "--show-secrets":
                show_secrets = True
                i += 1
            else:
                emit_error("USAGE_ERROR", f"unknown arg: {a}", exit_code=2)
        profile = inherited_value(ctx, "profile")
        try:
            data = get_config_list_data(
                layer=layer,
                keys_only=keys_only,
                show_secrets=show_secrets,
                config_path=config_path,
                profile=profile,
            )
        except DoxaError as exc:
            emit_doxa_error(exc)
        if data.get("error") == "INVALID_LAYER":
            emit_error(
                "INVALID_LAYER",
                f"--layer must be one of {', '.join(_VALID_LAYERS)}",
                exit_code=2,
            )
        emit_json(data)

    _dispatch(ctx, "list", args)


@config.command(name="path", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_path(ctx: click.Context, args: tuple[str, ...], as_json: bool) -> None:
    """Show config file path."""
    if as_json:
        from doxa_research.config_cmd import get_config_path_data
        from doxa_research.json_output import emit_error, emit_json

        validate_inherited_options(ctx, "config path", DEFAULT_HONOR)
        config_path_inh = inherited_value(ctx, "config_path")
        project = "--project" in args
        data = get_config_path_data(project=project, config_path=config_path_inh)
        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    _dispatch(ctx, "path", args)


@config.command(name="edit", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_edit(ctx: click.Context, args: tuple[str, ...], as_json: bool) -> None:
    """Open config file in $EDITOR."""
    if as_json:
        from doxa_research.config_cmd import get_config_edit_data
        from doxa_research.json_output import emit_error, emit_json

        validate_inherited_options(ctx, "config edit", DEFAULT_HONOR)
        config_path_inh = inherited_value(ctx, "config_path")
        project = "--project" in args
        data = get_config_edit_data(project=project, config_path=config_path_inh)
        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        if data["editor_exit_code"] != 0:
            emit_error(
                "EDITOR_FAILED",
                f"$EDITOR exited with code {data['editor_exit_code']}",
                {"exit_code": data["editor_exit_code"], "path": data["path"]},
                exit_code=1,
            )
        emit_json(data)

    _dispatch(ctx, "edit", args)


@config.command(name="help", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def config_help(ctx: click.Context, args: tuple[str, ...]) -> None:
    """Show config command help."""
    _dispatch(ctx, "help", args, NO_INHERITED_OPTIONS)


# ----------------------------------------------------------------------
# `doxa config profiles ...` subgroup (P21b)
# ----------------------------------------------------------------------

_MUTATOR_HONOR: frozenset[str] = frozenset({"config_path"})


@config.group(name="profiles", invoke_without_command=True)
@click.pass_context
def config_profiles(ctx: click.Context) -> None:
    """Manage configuration profiles."""
    if ctx.invoked_subcommand is None:
        validate_inherited_options(ctx, "config profiles", DEFAULT_HONOR)
        click.echo(
            "Error: config profiles requires an op "
            "(list|show|current|set-default|unset-default|add|set|unset|remove)",
            err=True,
        )
        ctx.exit(2)


@config_profiles.command(name="list")
@click.option("--show-shadowed", "show_shadowed", is_flag=True, help="Include shadowed profiles")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_profiles_list(ctx: click.Context, show_shadowed: bool, as_json: bool) -> None:
    """List configuration profiles."""
    from doxa_research.config_cmd import get_config_profile_list_data

    validate_inherited_options(ctx, "config profiles list", DEFAULT_HONOR)
    config_path_inh = inherited_value(ctx, "config_path")
    profile = inherited_value(ctx, "profile")
    try:
        data = get_config_profile_list_data(
            config_path=config_path_inh,
            profile=profile,
            show_shadowed=show_shadowed,
        )
    except DoxaError as exc:
        _emit_doxa_error_for_output_mode(ctx, exc, as_json=as_json)

    if as_json:
        from doxa_research.json_output import emit_json

        emit_json(data)

    active = data["active_profile"]
    rows = data["profiles"]
    if not rows:
        click.echo("No profiles defined")
        click.echo(f"Active profile: {active or '(none)'}")
        return
    for row in rows:
        marker = ""
        if row["active"]:
            marker = " [active]"
        elif row["shadowed"]:
            shadow_by = row["shadowed_by"]
            marker = f" [shadowed by {shadow_by['tier']}]"
        click.echo(f"{row['name']} ({row['tier']}){marker}")
    click.echo(f"Active profile: {active or '(none)'}")


@config_profiles.command(name="show")
@click.argument("name")
@click.option("--show-secrets", "show_secrets", is_flag=True, help="Reveal masked secret values")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_profiles_show(ctx: click.Context, name: str, show_secrets: bool, as_json: bool) -> None:
    """Show a single profile's contents."""
    from doxa_research.config_cmd import get_config_profile_show_data
    from doxa_research.json_output import emit_error

    validate_inherited_options(ctx, "config profiles show", _MUTATOR_HONOR)
    config_path_inh = inherited_value(ctx, "config_path")
    try:
        data = get_config_profile_show_data(
            name,
            show_secrets=show_secrets,
            config_path=config_path_inh,
        )
    except DoxaError as exc:
        _emit_doxa_error_for_output_mode(ctx, exc, as_json=as_json)

    if as_json:
        from doxa_research.json_output import emit_json

        if not data["found"]:
            emit_error(
                "PROFILE_NOT_FOUND",
                f"profile not found: {name}",
                {"profile": name, "available_profiles": data.get("available_profiles", [])},
                exit_code=1,
            )
        emit_json(data)

    if not data["found"]:
        click.echo(f"Error: profile not found: {name}", err=True)
        ctx.exit(1)
    import json as _json

    click.echo(_json.dumps(data["profile"], indent=2, sort_keys=True))


@config_profiles.command(name="current")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_profiles_current(ctx: click.Context, as_json: bool) -> None:
    """Show the runtime active profile and its source."""
    from doxa_research.config_cmd import get_config_profile_current_data

    validate_inherited_options(ctx, "config profiles current", DEFAULT_HONOR)
    config_path_inh = inherited_value(ctx, "config_path")
    profile = inherited_value(ctx, "profile")
    try:
        data = get_config_profile_current_data(
            config_path=config_path_inh,
            profile=profile,
        )
    except DoxaError as exc:
        _emit_doxa_error_for_output_mode(ctx, exc, as_json=as_json)

    if as_json:
        from doxa_research.json_output import emit_json

        emit_json(data)

    active = data["active_profile"]
    source = data["selection_source"]
    if not active or source == "none":
        click.echo("Active profile: (none)")
        return
    source_label = {
        "flag": "from --profile flag",
        "env": "from DOXA_PROFILE",
        "config": "from general.default_profile",
    }.get(source, f"from {source}")
    click.echo(f"Active profile: {active} ({source_label})")


@config_profiles.command(name="set-default")
@click.argument("name")
@click.option("--project", "project", is_flag=True, help="Write to project config")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_profiles_set_default(
    ctx: click.Context, name: str, project: bool, as_json: bool
) -> None:
    """Persist general.default_profile = NAME."""
    from doxa_research.config_cmd import get_config_profile_set_default_data
    from doxa_research.json_output import emit_error

    validate_inherited_options(ctx, "config profiles set-default", _MUTATOR_HONOR)
    config_path_inh = inherited_value(ctx, "config_path")
    try:
        data = get_config_profile_set_default_data(
            name,
            project=project,
            config_path=config_path_inh,
        )
    except ConfigProfileError as exc:
        if as_json:
            emit_doxa_error(exc)
        click.echo(f"Error: {exc.message}", err=True)
        if exc.suggestion:
            click.echo(f"Suggestion: {exc.suggestion}", err=True)
        ctx.exit(exc.exit_code)
    except DoxaError as exc:
        emit_doxa_error(exc)

    if as_json:
        from doxa_research.json_output import emit_json

        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    if data.get("error") == "PROJECT_CONFIG_CONFLICT":
        click.echo("Error: --config cannot be used with --project", err=True)
        ctx.exit(2)
    click.echo(f"Set default profile to '{data['default_profile']}'")


@config_profiles.command(name="unset-default")
@click.option("--project", "project", is_flag=True, help="Write to project config")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_profiles_unset_default(ctx: click.Context, project: bool, as_json: bool) -> None:
    """Remove general.default_profile from the target file."""
    from doxa_research.config_cmd import get_config_profile_unset_default_data
    from doxa_research.json_output import emit_error

    validate_inherited_options(ctx, "config profiles unset-default", _MUTATOR_HONOR)
    config_path_inh = inherited_value(ctx, "config_path")
    data = get_config_profile_unset_default_data(
        project=project,
        config_path=config_path_inh,
    )

    if as_json:
        from doxa_research.json_output import emit_json

        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    if data.get("error") == "PROJECT_CONFIG_CONFLICT":
        click.echo("Error: --config cannot be used with --project", err=True)
        ctx.exit(2)
    click.echo("Unset default profile")


@config_profiles.command(name="add")
@click.argument("name")
@click.option("--project", "project", is_flag=True, help="Write to project config")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_profiles_add(ctx: click.Context, name: str, project: bool, as_json: bool) -> None:
    """Create profile NAME (idempotent)."""
    from doxa_research.config_cmd import get_config_profile_add_data
    from doxa_research.json_output import emit_error

    validate_inherited_options(ctx, "config profiles add", _MUTATOR_HONOR)
    config_path_inh = inherited_value(ctx, "config_path")
    data = get_config_profile_add_data(
        name,
        project=project,
        config_path=config_path_inh,
    )

    if as_json:
        from doxa_research.json_output import emit_json

        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    if data.get("error") == "PROJECT_CONFIG_CONFLICT":
        click.echo("Error: --config cannot be used with --project", err=True)
        ctx.exit(2)
    if data["created"]:
        click.echo(f"Added profile '{name}'")
    else:
        click.echo(f"Already exists: profile '{name}'")


@config_profiles.command(name="set", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--project", "project", is_flag=True, help="Write to project config")
@click.option("--string", "force_string", is_flag=True, help="Treat VALUE as a string")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_profiles_set(
    ctx: click.Context,
    args: tuple[str, ...],
    project: bool,
    force_string: bool,
    as_json: bool,
) -> None:
    """Set a key on profile NAME."""
    from doxa_research.config_cmd import get_config_profile_set_data
    from doxa_research.json_output import emit_error

    validate_inherited_options(ctx, "config profiles set", _MUTATOR_HONOR)
    config_path_inh = inherited_value(ctx, "config_path")

    if len(args) != 3:
        message = "config profiles set takes NAME KEY VALUE"
        if as_json:
            emit_error("USAGE_ERROR", message, exit_code=2)
        click.echo(f"Error: {message}", err=True)
        ctx.exit(2)
    name, key, value = args

    data = get_config_profile_set_data(
        name,
        key,
        value,
        project=project,
        force_string=force_string,
        config_path=config_path_inh,
    )

    if as_json:
        from doxa_research.json_output import emit_json

        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    if data.get("error") == "PROJECT_CONFIG_CONFLICT":
        click.echo("Error: --config cannot be used with --project", err=True)
        ctx.exit(2)
    click.echo(f"Updated profile '{name}': {key} = {data['value']}")


@config_profiles.command(name="unset")
@click.argument("name")
@click.argument("key")
@click.option("--project", "project", is_flag=True, help="Write to project config")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_profiles_unset(
    ctx: click.Context, name: str, key: str, project: bool, as_json: bool
) -> None:
    """Remove a key from profile NAME."""
    from doxa_research.config_cmd import get_config_profile_unset_data
    from doxa_research.json_output import emit_error

    validate_inherited_options(ctx, "config profiles unset", _MUTATOR_HONOR)
    config_path_inh = inherited_value(ctx, "config_path")
    data = get_config_profile_unset_data(
        name,
        key,
        project=project,
        config_path=config_path_inh,
    )

    if as_json:
        from doxa_research.json_output import emit_json

        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    if data.get("error") == "PROJECT_CONFIG_CONFLICT":
        click.echo("Error: --config cannot be used with --project", err=True)
        ctx.exit(2)
    if data["removed"]:
        click.echo(f"Updated profile '{name}': unset {key}")
    else:
        click.echo(f"No such key in profile '{name}': {key}")


@config_profiles.command(name="remove")
@click.argument("name")
@click.option("--project", "project", is_flag=True, help="Write to project config")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_profiles_remove(ctx: click.Context, name: str, project: bool, as_json: bool) -> None:
    """Delete profile NAME (idempotent)."""
    from doxa_research.config_cmd import get_config_profile_remove_data
    from doxa_research.json_output import emit_error

    validate_inherited_options(ctx, "config profiles remove", _MUTATOR_HONOR)
    config_path_inh = inherited_value(ctx, "config_path")
    data = get_config_profile_remove_data(
        name,
        project=project,
        config_path=config_path_inh,
    )

    if as_json:
        from doxa_research.json_output import emit_json

        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    if data.get("error") == "PROJECT_CONFIG_CONFLICT":
        click.echo("Error: --config cannot be used with --project", err=True)
        ctx.exit(2)
    if data["removed"]:
        click.echo(f"Removed profile '{name}'")
    else:
        click.echo(f"No such profile: '{name}'")


@config.command(name="validate")
@click.argument("path", required=False, type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_validate(
    ctx: click.Context,
    path: Path | None,
    as_json: bool,
) -> None:
    """Validate a TOML config file against the schema.

    With no PATH, validates ``~/.config/doxa/doxa.config.toml`` (or the
    XDG_CONFIG_HOME equivalent). With PATH, validates that file. When PATH
    resolves to the shipped starter template, also runs a drift check
    against the schema's StarterField defaults.
    """
    from importlib.resources import files

    from doxa_research.cli_subcommands._config_validate import validate_config_file
    from doxa_research.json_output import emit_error, emit_json
    from doxa_research.paths import user_config_file

    target = path if path is not None else user_config_file()

    try:
        shipped = Path(str(files("doxa_research.data") / "starter.config.toml")).resolve()
    except (FileNotFoundError, ModuleNotFoundError):
        msg = "package data missing: doxa_research/data/starter.config.toml"
        if as_json:
            emit_error(
                "PACKAGE_DATA_MISSING",
                msg,
                details={"path": "doxa_research/data/starter.config.toml"},
            )
        click.echo(f"Error: {msg}", err=True)
        ctx.exit(1)

    try:
        target_resolved = target.resolve()
    except OSError:
        target_resolved = target
    drift = target_resolved == shipped

    result = validate_config_file(target, drift_check=drift)

    if as_json:
        if result.ok:
            emit_json(
                {
                    "path": str(result.path) if result.path else None,
                    "checks": list(result.checks),
                }
            )
        else:
            emit_error(
                result.error or "VALIDATION_FAILED",
                result.message,
                details=result.details if result.details else None,
            )
        return  # unreachable in practice but makes control flow explicit

    if result.ok:
        checks = " + ".join(result.checks) if result.checks else ""
        click.echo(f"OK: {result.path} ({checks})")
        return
    click.echo(f"Error: {result.message}", err=True)
    ctx.exit(1)
