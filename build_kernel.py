#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the shared Blair kernel, board modules and Android prebuilt layout."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('board', type=str.upper, choices=('FOGOS', 'RHODEP'))
    p.add_argument('--workspace', type=Path, default=HERE.parent)
    p.add_argument('-j', '--jobs', type=int, default=min(os.cpu_count() or 1, 192))
    p.add_argument('--llvm', type=Path, default=Path(os.environ.get('LLVM_DIR', '/usr/lib/llvm-18/bin')))
    p.add_argument('--prebuilt', type=Path, help='Output directory; default prebuilt/BOARD/6.1')
    p.add_argument('--android-tree', type=Path, help='Also install under device/motorola/DEVICE-kernel/6.1')
    p.add_argument('--plan', action='store_true', help='Print the build steps without executing them')
    args = p.parse_args()
    if not 1 <= args.jobs <= 192:
        p.error('--jobs must be between 1 and 192')
    return args


class Build:
    def __init__(self, args):
        self.args = args
        self.root = args.workspace.resolve()
        self.board = args.board
        self.profile_dir = HERE / 'profiles' / self.board
        self.profile = json.loads((self.profile_dir / 'profile.json').read_text())
        self.kernel = self.root / 'development/kernel'
        self.dev = self.root / 'development'
        self.tech = self.dev / 'mmi-w1uos'
        self.mmi = self.tech / 'motorola-kernel-modules'
        self.out = self.root / 'out'
        self.kout = self.out / 'kernel'
        self.collect_dir = self.out / self.board / 'modules'
        self.prebuilt = (args.prebuilt or self.root / 'prebuilt' / self.board / '6.1').resolve()
        self.available = {}
        self.env = os.environ.copy()
        self.env.update(ARCH='arm64', LLVM=str(args.llvm.resolve())+'/', LLVM_IAS='1',
                        KBUILD_BUILD_USER='sedona', KBUILD_BUILD_HOST='build')
        self.env['PATH'] = str(args.llvm.resolve())+os.pathsep+self.env.get('PATH', '')
        self.env['TMPDIR'] = str(self.out / 'tmp')
        self.llvm = args.llvm.resolve()

    def run(self, argv, **kwargs):
        argv = [str(x) for x in argv]
        print('+', ' '.join(argv), flush=True)
        return subprocess.run(argv, env=self.env, check=True, **kwargs)

    def make(self, *targets, flags='', **variables):
        command = ['make', '-C', self.kernel, 'O='+str(self.kout),
                   '-j'+str(self.args.jobs), 'LOCALVERSION=',
                   'PAHOLE='+self.env.get('PAHOLE', 'pahole')]
        if flags:
            command.append('KCFLAGS='+flags)
        command += [key+'='+str(value) for key, value in variables.items()]
        self.run([*command, *targets])

    def collect(self, directory):
        for item in (directory / 'modules.order').read_text().splitlines():
            source = Path(item)
            if not source.is_absolute():
                source = directory / source
            source = source.with_suffix('.ko')
            dest = self.collect_dir / source.name
            shutil.copy2(source, dest)
            self.available[source.stem.replace('-', '_')] = dest

    def module(self, path, flags='', **variables):
        path = Path(path)
        variables.setdefault('KBUILD_EXTRA_SYMBOLS', '')
        self.make('modules', M=path, flags=flags, **variables)
        self.collect(path)

    def check_dependencies(self):
        try:
            import clang.cindex
        except ImportError:
            raise RuntimeError('Missing Python libclang; run build/setup.sh first') from None
        for command in ('make','bc','bison','flex','perl','git','openssl','modinfo','dtc','fdtoverlay','fdtput','rsync'):
            if shutil.which(command, path=self.env['PATH']) is None:
                raise RuntimeError('Missing build dependency: '+command)
        for tool in ('clang','ld.lld','llvm-ar','llvm-nm','llvm-strip','llvm-objcopy'):
            if not (self.llvm/tool).is_file():
                raise RuntimeError('Missing LLVM tool: '+str(self.llvm/tool))
        if not shutil.which(self.env.get('PAHOLE', 'pahole'), path=self.env['PATH']):
            raise RuntimeError('Install pahole (dwarves), or set PAHOLE to its executable')
        for path in (self.kernel, self.dev/'peripherals', self.dev/'display', self.dev/'graphics',
                     self.dev/'securemsm', self.dev/'dsp', self.tech/'camera', self.mmi,
                     self.root/'tools/bionic/libc/kernel/tools/clean_header.py',
                     self.root/'tools/libufdt/utils/src/mkdtboimg.py'):
            if not path.exists():
                raise RuntimeError('Missing manifest project: '+str(path)+'; run repo sync')

    def configure_and_build_kernel(self):
        config = self.kernel/'arch/arm64/configs'
        self.run(['bash', self.kernel/'scripts/kconfig/merge_config.sh', '-m', '-O', self.kout,
                  config/'gki_defconfig', config/'vendor/blair_GKI.config',
                  config/'vendor/ext_config/moto-blair.config',
                  config/'vendor/ext_config/moto-blair-fogos.config'])
        self.make('olddefconfig')
        dt = 'vendor/qcom/'
        self.make('Image', 'modules', dt+'blair-moto-fogos-base.dtb',
                  *[dt+name for name in self.profile['dtbo']])
        self.collect(self.kout)

    def build_modules(self):
        from modules import build_all
        build_all(self)

    def stage(self):
        from prebuilt import stage
        stage(self)

    def execute(self):
        self.out.mkdir(exist_ok=True)
        (self.out/'tmp').mkdir(exist_ok=True)
        with (self.out/'.build.lock').open('w') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Another kernel build is using this workspace') from None
            self.check_dependencies()
            self.kout.mkdir(exist_ok=True)
            self.collect_dir.mkdir(parents=True, exist_ok=True)
            self.configure_and_build_kernel()
            self.build_modules()
            self.stage()
        print('BUILD COMPLETE: '+str(self.prebuilt), flush=True)


def main():
    args = parse_args()
    build = Build(args)
    if args.plan:
        print(json.dumps({'board':args.board, 'jobs':args.jobs, 'prebuilt':str(build.prebuilt),
            'steps':['configure shared 6.1 kernel','build Image, in-tree modules and board DTs',
                     'build retained Fogos and shared Motorola modules',
                     'build board camera/CCI and charging/touch/fingerprint modules',
                     'merge tech DTs and package ordered board DTBO',
                     'stage matching modules, load lists and sanitized Android headers',
                     *(['install Android prebuilt tree'] if args.android_tree else [])]}, indent=2))
        return
    try:
        build.execute()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print('BUILD FAILED: '+str(exc), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
