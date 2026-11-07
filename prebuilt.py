# SPDX-License-Identifier: Apache-2.0
"""Assemble a complete, matching prebuilt tree for the Android board config."""
from pathlib import Path
import re
import shutil
import subprocess
import sys


def names(path):
    return [line.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')]


def key(name):
    return Path(name).stem.replace('-','_')


def module_order(roots, available):
    result, done, visiting = [], set(), set()
    def visit(name):
        name=key(name)
        if name in done:return
        if name in visiting:raise RuntimeError('Module dependency cycle: '+name)
        if name not in available:raise RuntimeError('Required module was not built: '+name)
        visiting.add(name)
        path=available[name]
        dependencies=subprocess.check_output(['modinfo','-F','depends',str(path)],text=True).strip()
        for dependency in filter(None,dependencies.split(',')):visit(dependency)
        visiting.remove(name);done.add(name);result.append(path)
    for name in roots:visit(name)
    return result


def install_module(b,source,target,protected):
    shutil.copy2(source,target)
    b.run([b.llvm/'llvm-strip','--strip-debug',target])
    symbols=subprocess.check_output([str(b.llvm/'llvm-nm'),'--defined-only',str(target)],text=True)
    exports={part.removeprefix('__ksymtab_') for part in symbols.split() if part.startswith('__ksymtab_')}
    if exports & protected:
        config=(b.kout/'.config').read_text()
        algorithm=re.search(r'^CONFIG_MODULE_SIG_HASH="(\w+)"',config,re.M).group(1)
        b.run([b.kout/'scripts/sign-file',algorithm,b.kout/'certs/signing_key.pem',
               b.kout/'certs/signing_key.x509',target])


def merge_dt(b, dest):
    source=b.kout/'arch/arm64/boot/dts/vendor/qcom/blair-moto-fogos-base.dtb'
    result=dest/'dtb/blair-moto-fogos-base.dtb'
    work=b.out/b.board/'dt';work.mkdir(parents=True,exist_ok=True)
    sources=[b.tech/'dt-video/blair-vidc.dts',b.tech/'dt-bt/blair-bt.dts',
             b.tech/'dt-wlan/blair-cnss.dts',b.tech/'dt-data/blair-ipa.dts',
             b.kernel/'arch/arm64/boot/dts/vendor/qcom/blair-fogos-tech-fixups.dts']
    overlays=[]
    for index,dts in enumerate(sources):
        pp=work/(str(index)+'.dts');overlay=work/(str(index)+'.dtbo')
        b.run([b.llvm/'clang','-E','-P','-nostdinc','-undef','-D__DTS__','-x','assembler-with-cpp',
               '-I',dts.parent,'-I',b.kernel/'include','-I',b.kernel/'scripts/dtc/include-prefixes',
               '-I',b.kernel/'arch/arm64/boot/dts/vendor/qcom','-o',pp,dts])
        b.run(['dtc','-@','-q','-I','dts','-O','dtb','-o',overlay,pp]);overlays.append(overlay)
    b.run(['fdtoverlay','-i',source,'-o',result,*overlays])
    for spec in b.profile['dtb_delete']:
        node,prop=spec.rsplit(':',1)
        b.run(['fdtput','-d',result,node,prop])
    b.run([sys.executable,b.root/'tools/libufdt/utils/src/mkdtboimg.py','create',dest/'dtbo.img',
           '--page_size=4096','--version=0',
           *[b.kout/'arch/arm64/boot/dts/vendor/qcom'/name for name in b.profile['dtbo']]])


def stage(b):
    dest=b.prebuilt.with_name(b.prebuilt.name+'.building')
    if dest.exists():shutil.rmtree(dest)
    for subdir in ('dtb','modules','vendor_modules'):(dest/subdir).mkdir(parents=True,exist_ok=True)
    shutil.copy2(b.kout/'arch/arm64/boot/Image',dest/'Image')
    early=module_order(names(b.profile_dir/'modules.load.recovery'),b.available)
    vendor=module_order(names(b.profile_dir/'modules.load.vendor'),b.available)
    blocked=[]
    for line in names(b.profile_dir/'modules.blocklist'):
        parts=line.split()
        if len(parts)==2 and parts[0]=='blocklist' and key(parts[1]) in b.available:blocked.append(parts[1])
    all_modules=module_order([p.name for p in vendor+early]+blocked,b.available)
    protected=set(re.findall(r'"([^"]+)"',(b.kout/'include/generated/gki_module_protected_exports.h').read_text()))
    for source in all_modules:install_module(b,source,dest/'vendor_modules'/source.name,protected)
    for source in early:shutil.copy2(dest/'vendor_modules'/source.name,dest/'modules'/source.name)
    (dest/'modules.load.recovery').write_text(''.join(p.name+'\n' for p in early))
    # The board load list preserves modules intentionally delegated to vendor init.
    (dest/'modules.load.vendor').write_text(''.join(p.name+'\n' for p in vendor))
    shutil.copy2(b.profile_dir/'modules.blocklist',dest/'modules.blocklist')
    merge_dt(b,dest)
    from headers import stage_headers
    stage_headers(b,dest)
    if b.prebuilt.exists():
        backup=b.prebuilt.with_name(b.prebuilt.name+'.previous')
        if backup.exists():shutil.rmtree(backup)
        b.prebuilt.rename(backup)
    dest.rename(b.prebuilt)
    if b.args.android_tree:
        android=b.args.android_tree.resolve()
        if not (android/'build/envsetup.sh').is_file():raise RuntimeError('Not an Android source tree: '+str(android))
        target=android/'device/motorola'/(b.profile['device']+'-kernel')/'6.1'
        if target.is_symlink():raise RuntimeError('Android destination is a symlink; choose a checkout without a frozen-stage link')
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():shutil.rmtree(target)
        shutil.copytree(b.prebuilt,target)
        print('ANDROID PREBUILT INSTALLED: '+str(target),flush=True)
