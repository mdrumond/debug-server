"""Reusable CLI templates for repo bootstrapping."""

from __future__ import annotations

from textwrap import dedent

from client.config import ClientConfig

AGENT_SENTINEL_START = "<!-- DEBUG-SERVER:AGENT-INSTALL START -->"
AGENT_SENTINEL_END = "<!-- DEBUG-SERVER:AGENT-INSTALL END -->"
_DOCS_REPO = "https://github.com/debug-server/debug-server"
README_URL = f"{_DOCS_REPO}/blob/main/README.md"
CLI_DOCS_URL = f"{_DOCS_REPO}/blob/main/docs/cli.md"
DEFAULT_SPEC_TEMPLATE = (
    dedent(
        """
    # Repository Specification

    This repository follows the Debug Server workflow described in `AGENTS.md`.
    Keep `.codex/environment.md` and `.codex/SPEC.md` aligned with reality so
    downstream agents can bootstrap quickly.

    ## Workflow Overview

    1. Create new work items in `.codex/tasks/` using the provided template.
    2. Complete the work, document verification steps, and move the file to
       `.codex/done/` once finished.
    3. Re-run `debug-server agent install` whenever the shared Debug Server
       instructions change upstream.
    """
    ).strip()
    + "\n"
)


def render_agent_installation(config: ClientConfig, heading: str) -> str:
    """Render the reusable AGENTS.md section for Debug Server usage."""

    base_url = config.base_url or "https://debug-server.example"
    configure = f"debug-server configure --base-url {base_url} --token <DEBUG_SERVER_TOKEN>"
    if not config.verify_tls:
        configure += " --insecure"

    instructions = dedent(
        f"""
        {AGENT_SENTINEL_START}
        ## {heading}

        > This section is managed by `debug-server agent install`. Re-run the command
        > to refresh Debug Server requirements when they change upstream.

        ### 1. Install the CLI
        ```bash
        pip install -e .
        ```

        ### 2. Configure defaults for this environment
        ```bash
        {configure}
        ```

        ### 3. Seed or refresh Debug Server instructions in this repo
        ```bash
        debug-server agent install .
        ```

        Additional resources maintained in the Debug Server repository:
        - [Debug Server README]({README_URL})
        - [Debug Server CLI docs]({CLI_DOCS_URL})
        {AGENT_SENTINEL_END}
        """
    ).strip()
    return instructions + "\n"
