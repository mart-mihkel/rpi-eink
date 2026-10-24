# Agents

Raspberry Pi 4 dashboard for a Waveshare 7.3" Spectra 6 e-Paper panel (800x480, 6 ink colors). A single uv-managed Python 3.15 package (`eink`) fetches Open-Meteo weather, renders a Jinja/SVG dashboard through CairoSVG, quantizes it to the panel's ink palette, and drives the panel over SPI/GPIO.

## Layout

```
src/eink/
  main.py           # rich-click app, one command per script, imports them lazily
  constants.py      # global constants
  types.py          # shared types
  logging.py        # project logger and logging/traceback setup
  convert.py        # resize/crop and quantize images to the panel palette
  weather/          # Open-Meteo client, pydantic schemas, SVG renderer, templates/
  scripts/          # command implementations
  vendor/           # vendored Waveshare SPI/GPIO driver
stubs/spidev.pyi    # types for the Linux-only spidev dependency
test/               # flat pytest suite; test/vendor/ has GPIO/SPI fakes
data/               # assets and images
SETUP.md            # Raspberry Pi GPIO/SPI setup; read before touching hardware code
```

## Commands

```bash
just sync         # uv sync virtualenv, install prek hooks
just prek         # pre-commit checks, all files by default
just test [args]  # pytest with varitaic arg passthrough
```

## Conventions

- Fallible code uses `returns`: `@safe`/`@future_safe` functions return `Result`/`IOResult`, and `.unwrap()` appears only at the CLI boundary. Tests await future-safe calls, then match on `IOSuccess(Success(...))` / `IOFailure(Failure(...))`.
- Logging goes through `eink.logging.logger`; the group callback calls `setup_logging()`, and each command applies `--log-level` with `logger.setLevel(log_level.upper())`.
- The dashboard template uses `StrictUndefined`: any variable it references must be a field on `RenderContext`/`HourlyContext` in `weather/schemas.py`.
- Pydantic models describing API payloads use `extra="forbid"`; keep new response models equally strict.
- The six real ink colors live in `ImageConverter._panel_colors`; the template draws weather icons as inline SVG macros.
- Python docstrings are a single high-level line for simple objects; use numpy sections only when parameters, returns, or raises need explanation.
- Add tests to the closest existing file in `test/` rather than creating new modules or packages.
- Pytest turns `DeprecationWarning`, `FutureWarning`, `RuntimeWarning`, and `UserWarning` into errors.
- Ruff selects `ALL`; only `COM812`, `CPY001`, `D203`, and `D212` are ignored, and `test/**` additionally allows missing docstrings, asserts, boolean positional arguments, and private access.

## Guidelines

- **NEVER** run git commands.
- Ask for permission before ignoring linter or typechecker errors (`noqa`, `ty: ignore`).
- Use type casting or asserts if needed instead of loosening a type.
- Always add precise and exhaustive type annotations to everything.
- Prefer exhaustive types over bare containers, a pandera-typed `DataFrame[Schema]` over a plain `DataFrame`. Use precise generics or designated typing classes over bare `list`/`tuple`/`dict`, don't be afraid of creating an entire `NamedTuple`, `TypedDict` or `Protocol` for small use cases. For bigger use cases use dataclasses or pydantic models.
- Avoid writing walls of text with rich markdown syntax when documenting code objects.
- All significant changes must be tested. Add or update focused tests for semantic changes when existing coverage does not already establish the intended behavior.
- Look to see if your tests could go in an existing file before adding a new file for your tests.
- Get your tests to pass. If you didn't run the tests, your code does not work.
- Follow existing code style. Check neighboring files for patterns.
- Run `just prek` after making changes.
- Before writing significant amounts of new code, look for existing utilities or mechanisms that could solve the problem. Avoid expanding the task to unrelated issues, but do not confuse keeping the task focused with minimizing the size of the implementation. Prefer addressing the underlying architectural problem over adding a localized workaround, even when doing so requires a substantial refactor or rearchitecture. Ask the user for guidance if in doubt about whether to attempt a larger refactor or not.
- Try hard to avoid patterns that require `getattr` or `setattr`. Instead, try to encode those constraints in the type system. Don't be afraid to write code that's more verbose or requires largeish refactors if it enables you to avoid these unsafe calls.
- Don't use comments to narrate code, but do use them to explain invariants and why something unusual was done a particular way
- Make sure that a comment will make sense to somebody who's reading the code for the first time. Prefer plain language, avoid jargon, and don't be afraid to be more verbose if it's necessary to explain something well.
- Avoid writing walls of rich markdown text when documenting code objects. Use a docstring format.
- Try not to create module level constatns, inline them or create a function parameter with a default value.
