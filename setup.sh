#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python3 -m venv "$here/.venv"
"$here/.venv/bin/python3" -m pip install --requirement "$here/requirements.txt"
