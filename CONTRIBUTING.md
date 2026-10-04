# Contributing

Pull requests are welcome.

## Before you start

By opening a pull request you agree to the terms in [LICENSE](LICENSE): your
work is published under the same Attribution-NonCommercial License, you keep
the copyright in it, and you confirm it is your own original work with no
third-party rights attached.

## Scope

The tools stay deliberately small and dependency-light. Before proposing
something new, keep it in mind:

- **Python stdlib and `httpx`.** No new runtime dependency without a strong
  reason — every dependency is one more install for the user.
- **Direct API calls.** No relay server, no MCP bridge, no Docker.
- **French docstrings, English identifiers.** Function and parameter names stay
  English; the prose a model reads stays French.
- **Valves for all configuration.** Nothing hardcoded, nothing read from
  environment variables that the admin cannot see in the UI.
- **Refuse without leaking.** A tool should fail with a clear message rather
  than silently degrading, and never print a token, a secret or a full body
  it was not asked to read.

## Before you open the pull request

- Tested against a real Open WebUI instance (`0.4.0` or later) with the tool
  actually enabled.
- `python -m py_compile tools/<your-file>.py` passes.
- The docstring header at the top of the file is up to date: `title`,
  `description`, `version`, `requirements`, and the OAuth setup notes if they
  changed.
- Bumped `version` in the header.
- The README table and method list reflect what you added or changed.

## Commit messages

Short, imperative, subject under ~70 characters: `Add ICS export to calendar
tool`, not `Added a bunch of stuff`. Explain the why in the body if the diff
does not make it obvious.

## What will not be accepted

- Anything requiring a network call to a server you control.
- Anything that weakens the "read only after consent" instructions in the
  Gmail docstrings.
- Large formatting-only diffs, and reformatting of untouched files.
- Anything that cannot be reviewed because it is not described in the pull
  request body.