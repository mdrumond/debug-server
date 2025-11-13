# Spec updates: Conda-first workers & auth

- documented that workers default to standalone processes with dedicated workspace folders and Conda environments, while Docker remains optional.
- required clients to declare dependencies via user-level package managers (Conda, pip, pipx, uv, npm/pnpm/yarn, cargo, etc.).
- described the bearer-token authentication model, distribution guidance for CLI/MCP/VS Code, and how session auditing ties back to token owners.
- updated `.codex/environment.md` to reflect the Conda-first installation story and leave placeholders for concrete commands.
