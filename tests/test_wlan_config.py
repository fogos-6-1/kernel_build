# SPDX-License-Identifier: Apache-2.0
import shutil
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wlan_config import generate


class WlanConfigTest(unittest.TestCase):
    def test_string_defaults_and_overrides_compile_as_strings(self):
        compiler=shutil.which('clang-18') or shutil.which('clang')
        if compiler is None:self.skipTest('clang is not installed')
        for override in ('', 'CONFIG_MULTI_IF_NAME="override"\n'):
            with self.subTest(override=override), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);wlan=root/'wlan';(wlan/'configs').mkdir(parents=True)
                (wlan/'Kconfig').write_text('config MULTI_IF_NAME\n    string\n    default adrastea\n')
                (wlan/'configs/blair_gki_wlan_defconfig').write_text(override)
                generate(wlan,root/'kernel',root/'generated')
                source=root/'probe.c';source.write_text('const char *name = CONFIG_MULTI_IF_NAME;\n')
                subprocess.run([compiler,'-Werror','-fsyntax-only','-include',str(root/'generated/autoconf.h'),str(source)],check=True)


if __name__=='__main__':unittest.main()
