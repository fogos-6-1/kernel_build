# SPDX-License-Identifier: Apache-2.0
"""External-module build recipes for the Blair board family."""
from pathlib import Path
import re

WARN = '-Wno-error=format -Wno-error=missing-prototypes'


def wlan_config(build, module):
    from wlan_config import generate
    generated = build.out/'qcacld-config'
    generate(module, build.kernel, generated)
    return generated


def build_all(b):
    d, t, k = b.dev, b.tech, b.kernel
    b.module(d/'peripherals', KERNEL_SRC=k,
             CONFIG_INPUT_TOUCHSCREEN_MMI='y', CONFIG_ILITEK_ESD='y',
             CONFIG_INPUT_ILI_ENABLE_DOUBLE_TAP='y',
             CONFIG_INPUT_CHIPONE_0FLASH_MMI_ENABLE_DOUBLE_TAP='y',
             CONFIG_BOARD_USES_DOUBLE_TAP_CTRL='y',
             CONFIG_INPUT_MISC_FPC1020_SAVE_TO_CLASS_DEVICE='y')
    common = d/'peripherals/Module.symvers'
    b.module(d/'graphics', KGSL_PATH=d/'graphics', KERNEL_SRC=k, CONFIG_QCOM_KGSL='m')
    b.module(d/'display', DISPLAY_ROOT=d/'display', KERNEL_SRC=k, CONFIG_DRM_MSM='m')
    b.module(d/'securemsm', flags='-DSMCINVOKE_TRACE_INCLUDE_PATH='+str(d/'securemsm/smcinvoke/compat'),
             SSG_MODULE_ROOT=d/'securemsm', KERNEL_SRC=k)
    b.module(d/'dsp', flags='-DDSP_TRACE_INCLUDE_PATH='+str(d/'dsp/dsp'), DSP_ROOT=d/'dsp', KERNEL_SRC=k)
    mmrm=t/'mmrm'
    b.module(mmrm/'driver', flags=WARN+' -include '+str(mmrm/'config/waipiommrmconf.h'),
             MMRM_ROOT=mmrm, CONFIG_MSM_MMRM='y')
    b.module(t/'video', flags=WARN, VIDEO_ROOT=t/'video',
             KBUILD_EXTRA_SYMBOLS=mmrm/'driver/Module.symvers')
    b.module(t/'bt', flags=WARN, BT_ROOT=t/'bt', CONFIG_MSM_BT_POWER='m', CONFIG_BTFM_SLIM='m')
    platform=t/'wlan/platform'
    b.module(platform, flags=WARN, WLAN_PLATFORM_ROOT=platform,
             CONFIG_CNSS_OUT_OF_TREE='y', CONFIG_ICNSS2='m', CONFIG_ICNSS2_QMI='y',
             CONFIG_CNSS_QMI_SVC='m', CONFIG_CNSS_UTILS='m', CONFIG_CNSS_GENL='m',
             CONFIG_WCNSS_MEM_PRE_ALLOC='m')
    wlan=t/'wlan/qcacld-3.0'
    config=wlan_config(b,wlan)
    flags=(WARN+' -Wno-macro-redefined -D__ANDROID_COMMON_KERNEL__ -include '+str(config/'autoconf.h')+
           ' -include '+str(wlan/'configs/config_to_feature.h')+' -include '+str(config/'grep_defines.h'))
    b.module(wlan, flags=flags, WLAN_ROOT=wlan, MODNAME='wlan', WLAN_PROFILE='blair_gki_wlan',
             WLAN_CFG_OVERRIDE=(config/'overrides.txt').read_text().strip(),
             CONFIG_QCA_CLD_WLAN='m', CONFIG_QCA_WIFI_ISOC='0', CONFIG_QCA_WIFI_2_0='1',
             CONFIG_CNSS_OUT_OF_TREE='y', CONFIG_REMOVE_PKT_LOG='n', QCA_WIFI_FTM_NL80211='y',
             BUILD_DIAG_VERSION='y', CONFIG_FEATURE_BLACKLIST_MGR='n', CONFIG_MPC_UT_FRAMEWORK='n',
             KBUILD_EXTRA_SYMBOLS=platform/'Module.symvers')
    mem=t/'datarmnet-ext/mem'
    b.module(mem, CONFIG_RMNET_MEM='m')
    ipa=t/'dataipa'
    out=b.out/'dataipa-build';out.mkdir(exist_ok=True)
    (out/'Kbuild').write_bytes((Path(__file__).parent/'dataipa.mk').read_bytes())
    for name in ('gsi','ipa'):
        link=out/name;target=ipa/'drivers/platform/msm'/name
        if not link.exists():link.symlink_to(target,target_is_directory=True)
    b.module(out, flags=WARN, DATAIPA_ROOT=ipa, RMNET_MEM_ROOT=mem,
             CONFIG_GSI='m', CONFIG_IPA_CLIENTS_MANAGER='m', CONFIG_IPA_WDI_UNIFIED_API='y',
             CONFIG_RMNET_IPA3='y', CONFIG_RNDIS_IPA='m', CONFIG_IPA3_REGDUMP='y',
             CONFIG_IPA3_REGDUMP_IPA_5_5='y', KBUILD_EXTRA_SYMBOLS=mem/'Module.symvers')
    core=t/'datarmnet/core'
    flags=(WARN+' -I'+str(ipa/'drivers/platform/msm/include')+' -I'+str(ipa/'drivers/platform/msm/include/uapi')+
           ' -I'+str(mem)+' -DRMNET_TRACE_INCLUDE_PATH='+str(core)+' -DCONFIG_RMNET_LA_PLATFORM=1')
    b.module(core, flags=flags, KBUILD_EXTRA_SYMBOLS=str(out/'Module.symvers')+' '+str(mem/'Module.symvers'))
    flags=WARN+' -I'+str(ipa/'drivers/platform/msm/include')+' -I'+str(mem)+' -DCONFIG_RMNET_LA_PLATFORM=1'
    for name in ('offload','shs','perf','perf_tether','wlan'):
        b.module(t/'datarmnet-ext'/name, flags=flags, RMNET_CORE_INC_DIR=core,
                 KBUILD_EXTRA_SYMBOLS=str(core/'Module.symvers')+' '+str(out/'Module.symvers'))
    top=b.out/'mmi-top';(top/'motorola/kernel').mkdir(parents=True,exist_ok=True)
    (top/'kernel_platform').mkdir(exist_ok=True)
    for link,target in ((top/'motorola/kernel/modules',b.mmi),(top/'kernel_platform/common',k)):
        if not link.exists():link.symlink_to(target,target_is_directory=True)
    for name in ('moto_binder','moto_mmap_fault','power/wakeup_sources','moto_f_usbnet','moto_netopt/con_dfpar'):
        b.module(b.mmi/'drivers'/name,flags=WARN,ANDROID_BUILD_TOP=top)
    if b.board=='RHODEP':
        rhodep(b,common,top)
    camera=t/'camera'
    flags=WARN+' -DCONFIG_CAM_SENSOR_LEGACY_PROBE_RESERVED=1 -DCONFIG_CAMERA_FLASH_IIC_COMPATIBLE=1 -DCONFIG_MOT_SENSOR_PRE_POWERUP=1'
    variables={}
    if b.board=='RHODEP':
        flags+=' -DCONFIG_CAMERA_FLASH_PWM=1';variables['CONFIG_CAMERA_FLASH_PWM']='y'
    b.run(['make','-C',camera,'cam_generated_h'])
    b.module(camera,flags=flags,CAMERA_KERNEL_ROOT=camera,KERNEL_ROOT=k,MODNAME='camera',**variables)
    includes=sorted(set(str(x.parent) for x in camera.rglob('*.h')))
    flags+=' '+ ' '.join('-I'+x for x in includes)
    flags+=' -I'+str(camera/'include/uapi')+' -I'+str(camera/'include/uapi/camera')
    flags+=' -DCONFIG_SPECTRA_ISP=1 -DCONFIG_SPECTRA_TFE=1 -DCONFIG_SPECTRA_OPE=1 -DCONFIG_SPECTRA_SENSOR=1'
    b.module(b.mmi/'drivers/media/platform/msm/camera/cam_sensor_module/cam_cci',flags=flags,
             ANDROID_BUILD_TOP=top,KERNEL_CAMERA_DRIVER_PATH=camera/'drivers',
             KBUILD_EXTRA_SYMBOLS=camera/'Module.symvers')


def rhodep(b,common,top):
    d=b.mmi/'drivers'
    def module(name, symbols=common, **options):
        b.module(d/name,flags=WARN+' -Wno-error=unused-but-set-variable',
                 ANDROID_BUILD_TOP=top,TOP=top,TARGET_PRODUCT='rhodep_g',KBUILD_EXTRA_SYMBOLS=symbols,**options)
    module('usb/typec/adapter_class')
    adapter=d/'usb/typec/adapter_class/Module.symvers'
    module('power/mmi_charger')
    charger=d/'power/mmi_charger/Module.symvers'
    module('power/mmi_discrete_charger',f'{common} {adapter} {charger}')
    module('power/qpnp_adaptive_charge',f'{common} {charger}',CONFIG_USE_MMI_CHARGER='y')
    discrete=d/'power/mmi_discrete_charger/Module.symvers'
    module('usb/typec/mmi_tcpc',f'{common} {adapter} {discrete}',CONFIG_TCPC_CLASS='m',
           CONFIG_USB_POWER_DELIVERY='y',CONFIG_TCPC_SGM7220='m',CONFIG_TCPC_RT1711H='m',CONFIG_RT_PD_MANAGER='m')
    for name in ('sgm4154x_chg_mmi','bq2589x_chg_mmi'):
        module('power/'+name,f'{common} {discrete}',CONFIG_MMI_QC3P_TURBO_CHARGER='y')
    module('power/bq2597x_mmi_iio')
    module('power/mmi_discrete_turbo_charger',f'{common} {adapter}')
    for name in ('cw2217b_fg_mmi','sm5602_fg_mmi'):module('power/'+name)
    module('regulator/wl2868c')
    module('input/touchscreen/touchscreen_mmi',CONFIG_DRM_PANEL_EVENT_NOTIFICATIONS='y',CONFIG_BOARD_USES_DOUBLE_TAP_CTRL='y')
    touchscreen=d/'input/touchscreen/touchscreen_mmi/Module.symvers'
    module('input/touchscreen/goodix_berlin_mmi',f'{common} {touchscreen}',CONFIG_INPUT_TOUCHSCREEN_MMI='y',
           CONFIG_TOUCHSCREEN_GOODIX_BRL_SPI='y',CONFIG_GTP_LIMIT_USE_SUPPLIER='y',CONFIG_GOODIX_ESD_ENABLE='y',
           CONFIG_GTP_LAST_TIME='y',CONFIG_BOARD_USES_DOUBLE_TAP_CTRL='y',CONFIG_DRM_PANEL_EVENT_NOTIFICATIONS='y')
    for name in ('rbs_fps_mmi','focal_fps_mmi'):module('input/misc/'+name)
