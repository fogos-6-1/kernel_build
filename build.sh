#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
here=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)
python=${PYTHON:-$here/.venv/bin/python3}
if [[ ! -x "$python" ]]; then python=python3; fi
exec "$python" "$here/build_kernel.py" --workspace "$(dirname -- "$here")" "$@"
