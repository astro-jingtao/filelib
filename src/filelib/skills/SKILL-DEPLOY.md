# Deploying the Skills Shipped in This Package

The `filelib` Python package ships Claude Agent Skills as package data, inside the installed package under `filelib.skills`. This guide is written for the agent (or person) deploying them on a machine that carries no dedicated skill-deployment tooling — everything needed is in this file.

Currently shipped: **`filelib`** — the agent-facing usage guide for the `filelib` package (directory scanning, move/copy/remove/merge with dry-run previews and conflict policies, path and content comparison, HTTP downloads, image corruption checks, and the `filelib` CLI).

## Find the skills root

All paths below resolve through the **installed package**, never a repository checkout. Print the absolute skills root with:

```powershell
python -m filelib.skills
```

```text
C:\...\site-packages\filelib\skills
Deployment guide: C:\...\site-packages\filelib\skills\SKILL-DEPLOY.md
```

The rest of this guide writes `<skills-root>` for that printed path. Without the module, the equivalent one-liner: `python -c "from importlib.resources import files; print(files('filelib') / 'skills')"`.

## What a skill entry looks like

Each skill occupies two layers under `<skills-root>`:

```text
<skills-root>/
└── <name>/
    ├── skill/            the skill proper — SKILL.md plus supporting files
    └── meta.yaml         external-dependency metadata — read, never deployed
```

Only `<skills-root>/<name>/skill/` is deployed. `meta.yaml` stays behind: it declares what the skill expects from its environment, and you read it before linking (next section).

## Deployment is a directory link

Make a skill visible to Claude Code by linking its `skill/` directory into a skills directory:

| target | link path | points at |
| ------ | --------- | --------- |
| user level (every project) | `~/.claude/skills/<name>` | `<skills-root>/<name>/skill` |
| project level (one project) | `<project>/.claude/skills/<name>` | same target |

Prefer a link over a copy — a link reflects the installed package as it is upgraded; a copy drifts the moment either side changes. When a link is impossible (privilege, filesystem), copy the directory instead and note that package upgrades will not reach the copy.

Commands — replace `<skills-root>` with the printed path:

Linux / macOS:

```bash
ln -s <skills-root>/filelib/skill ~/.claude/skills/filelib
```

Windows (PowerShell):

```powershell
New-Item -ItemType SymbolicLink -Path "$HOME\.claude\skills\filelib" -Target "<skills-root>\filelib\skill"
```

Windows requires Developer Mode or the "Create symbolic links" account right to create a symlink; a failure mentioning privilege or WinError 1314 means neither is present — enable one, or fall back to a copy:

```powershell
Copy-Item -Recurse <skills-root>\filelib\skill "$HOME\.claude\skills\filelib"
```

Create a directory symlink, never a Windows junction: recursive removers (`git worktree remove`, `git clean`) walk through a junction into its target and can delete the package's content, while a symlink is removed as the link itself.

## Before linking: read meta.yaml

`<skills-root>/<name>/meta.yaml` declares the skill's expectations of its environment:

| field | meaning | what you do before deploying |
| ----- | ------- | ---------------------------- |
| `depends-on` | other skills this one hard-requires to function | deploy them together — the same link procedure for each |
| `requires` | environment requirements | per entry: `home: default` (or no `home`) → verify on this machine now (run the entry's `check:` command when present; otherwise by its `kind` — a python version spec, an importable package name, a command on PATH, an OS); `check: manual` → verify by hand following the entry's `note`; `home: project-env` → nothing to do here — the skill verifies it inside the target project at use time; a `platform:` naming another OS → the entry does not exist here |
| `claude-md` | content the environment's CLAUDE.md should carry | land it in the CLAUDE.md at its `scope` — global → the user's `~/.claude/CLAUDE.md`, project → the target project's `CLAUDE.md`. Check for equivalent existing content first; insert only what is missing, wrapped in the marker pair below. The inserted text states WHAT the discipline is and names the skill — the full HOW lives in the skill body, never in CLAUDE.md |
| `integrates-with`, `notes` | informational linkage and operator notes | read; no action |

For `filelib`, the `requires` entry names the `filelib` console script (`check: filelib --help`); it is provided by the very package this skill ships with — when it is missing, the interpreter in use does not have `filelib` installed (`pip show filelib`; install the package, or select the environment where it is installed).

A `kind: os` entry naming an OS that is not this machine's means this platform does not support the skill — deploying it is a conscious choice (it stays dormant off its platform), or skip it.

claude-md marker pair — wrap inserted content so future readers can recognize machine-landed blocks:

```markdown
<!-- agent-skill:<skill>/<id> -->
…content…
<!-- /agent-skill:<skill>/<id> -->
```

An unsatisfied `depends-on` or `requires` entry is a report to the user — the user fixes the gap or consciously continues; never a silent skip. An `install:` command on a missing requirement runs only after the user confirms.

## Safety rules

- Show the plan first — which skills, which links, which findings — before creating anything.
- A real directory or file already sitting at a link destination is a conflict: report it, never delete it. The most you may do, with the user's knowledge, is rename it aside (`<name>.bak.<timestamp>`).
- The procedure is idempotent — re-running it leaves an existing correct link alone.

## After linking

- Verify each deployment: `<skills-dir>/<name>/SKILL.md` is reachable through the link, and the frontmatter `name:` equals `<name>`.
- To remove a deployment, remove the link itself — on Windows, confirm first that it is a symlink rather than a junction: `Get-Item <path> | Select-Object LinkType` should show `SymbolicLink`.
