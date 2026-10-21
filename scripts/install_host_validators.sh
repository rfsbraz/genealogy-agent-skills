#!/usr/bin/env bash
# Install the pinned host validators that scripts/run_host_validators.py runs.
# Usage: scripts/install_host_validators.sh TOOLS_DIR
# Needs Python 3.10+ with pip, Node.js 22+ with npm, and curl.
# Writes TOOLS_DIR/quick_validate.py and installs the claude CLI under TOOLS_DIR/npm.
set -euo pipefail

SKILLS_REF_VERSION=0.1.1
PYYAML_VERSION=6.0.3
CLAUDE_CODE_VERSION=2.1.306
# anthropics/skills commit and the SHA-256 of quick_validate.py at that commit.
SKILLS_COMMIT=dbd4588f9e1033efb41dad4bef2f7947c8993d44
QUICK_VALIDATE_SHA256=67cf5703402013936c8fb75ad6a1afecd8841d45cc5e606b634eb05825fde365

tools="${1:?usage: $0 TOOLS_DIR}"
mkdir -p "$tools"

python -m pip install --quiet "skills-ref==${SKILLS_REF_VERSION}" "pyyaml==${PYYAML_VERSION}"

curl -fsSL -o "$tools/quick_validate.py" \
  "https://raw.githubusercontent.com/anthropics/skills/${SKILLS_COMMIT}/skills/skill-creator/scripts/quick_validate.py"
echo "${QUICK_VALIDATE_SHA256}  $tools/quick_validate.py" | sha256sum -c -

npm install --silent --no-fund --no-audit --prefix "$tools/npm" "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"

agentskills --version
"$tools/npm/node_modules/.bin/claude" --version
