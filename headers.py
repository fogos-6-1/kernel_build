# SPDX-License-Identifier: Apache-2.0
"""Export the UAPI layout used by the legacy APR/Q6 Android HALs."""
import os
from pathlib import Path
import shutil
import sys
import tarfile


def stage_headers(b, dest):
    exported=b.out/'headers-install'
    b.make('headers_install',INSTALL_HDR_PATH=exported)
    source=exported/'include'
    headers=dest/'kernel-headers'
    shutil.copytree(source,headers)
    toolroot=b.root/'tools'
    bionic=toolroot/'bionic/libc/kernel/tools'
    os.environ['ANDROID_BUILD_TOP']=str(toolroot)
    # Bionic expects its bundled Python bindings and library in this layout.
    import clang
    from clang.cindex import Cursor, conf
    # Android's sanitizer uses the newer convenience method; LLVM 18 exposes
    # the identical null-cursor check through its C API.
    if not hasattr(Cursor, 'is_null'):
        Cursor.is_null = lambda self: self == conf.lib.clang_getNullCursor()
    bindings=Path(clang.__file__).resolve().parent
    library=bindings/'native/libclang.so'
    if not library.is_file():
        raise RuntimeError('Install the pinned libclang package with build/setup.sh')
    clangdir=toolroot/'prebuilts/clang/host/linux-x86/clang-stable/lib'
    clangdir.mkdir(parents=True,exist_ok=True)
    link=clangdir/'libclang.so'
    if link.is_symlink():link.unlink()
    if not link.exists():link.symlink_to(library)
    sys.path.insert(0,str(bionic))
    from clean_header import cleanupFile, kernel_structs_to_remove
    kernel_structs_to_remove['sched_param']=None
    previous=Path.cwd();os.chdir(toolroot)
    try:
        for header in source.rglob('*.h'):
            rel=header.relative_to(source)
            cleaner=str(rel)
            if cleaner.startswith('asm/'):cleaner='asm-arm64/'+cleaner[4:]
            cleaned=cleanupFile(str(headers/rel),str(header),cleaner)
            if cleaned is None:raise RuntimeError('Cannot sanitize '+str(header))
            (headers/rel).write_text(cleaned)
        for path in [b.dev/'display/include/uapi',b.dev/'graphics/include/uapi',
                     b.dev/'securemsm/include/uapi',b.dev/'dsp/include/uapi']:
            if path.exists():shutil.copytree(path,headers,dirs_exist_ok=True)
        audio=b.kernel/'techpack/audio/include/uapi/audio'
        shutil.copytree(audio,headers,dirs_exist_ok=True)
        for header in audio.rglob('*.h'):
            rel=header.relative_to(audio)
            cleaned=cleanupFile(str(headers/rel),str(header),str(rel))
            if cleaned is None:raise RuntimeError('Cannot sanitize '+str(header))
            (headers/rel).write_text(cleaned)
    finally:
        os.chdir(previous)
    ipa=b.tech/'dataipa/drivers/platform/msm/include/uapi'
    shutil.copytree(ipa,headers,dirs_exist_ok=True)
    shutil.copy2(Path(__file__).parent/'include/linux/rmnet_data.h',headers/'linux/rmnet_data.h')
    with (headers/'linux/msm_audio.h').open('a') as f:
        f.write('\n#ifndef IOCTL_MAP_PHYS_ADDR\n'
                '#define IOCTL_MAP_PHYS_ADDR _IOW(AUDIO_IOCTL_MAGIC, 97, int)\n'
                '#define IOCTL_UNMAP_PHYS_ADDR _IOW(AUDIO_IOCTL_MAGIC, 98, int)\n'
                '#endif\n')
    version={}
    for line in (b.kernel/'Makefile').read_text().splitlines():
        if ' = ' in line:
            key,value=line.split(' = ',1)
            if key in ('VERSION','PATCHLEVEL','SUBLEVEL'):version[key]=value
    (headers/'Makefile').write_text(''.join(key+' = '+version[key]+'\n' for key in ('VERSION','PATCHLEVEL','SUBLEVEL')))
    (headers/'Kbuild').write_text('# SPDX-License-Identifier: GPL-2.0-only WITH Linux-syscall-note\nheader-y += display/\n')
    config=headers/'arch/arm64/configs';config.mkdir(parents=True)
    shutil.copy2(b.kout/'.config',config/'fogos_prebuilt_defconfig')
    with tarfile.open(dest/'kernel-uapi-headers.tar.gz','w:gz') as archive:
        archive.add(headers,arcname='usr/include')
