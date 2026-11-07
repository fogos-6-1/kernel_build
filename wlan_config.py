# SPDX-License-Identifier: Apache-2.0
"""Materialize the Blair qcacld Kconfig and DDK feature probes for make."""
import re
import json

FEATURES = [
 ('kernel/sched/walt/walt.c','walt_get_cpus_taken','WALT_GET_CPU_TAKEN_SUPPORT'),
 ('net/wireless/nl80211.c','nl80211_validate_key_link_id','CFG80211_MLO_KEY_OPERATION_SUPPORT'),
 ('include/net/cfg80211.h','struct link_station_parameters','CFG80211_LINK_STA_PARAMS_PRESENT'),
 ('include/uapi/linux/nl80211.h','NL80211_EXT_FEATURE_PUNCT','NL80211_EXT_FEATURE_PUNCT_SUPPORT'),
 ('include/net/cfg80211.h','unsigned int link_id, u16 punct_bitmap','CFG80211_RU_PUNCT_NOTIFY'),
 ('include/uapi/linux/nl80211.h','NL80211_EXT_FEATURE_AUTH_AND_DEAUTH_RANDOM_TA','CFG80211_EXT_FEATURE_AUTH_AND_DEAUTH_RANDOM_TA'),
]


def generate(wlan, kernel, dest):
    values, types, current = {}, {}, None
    for line in (wlan/'Kconfig').read_text().splitlines():
        match=re.match(r'config\s+(\w+)',line)
        if match:
            current=match[1];continue
        match=re.match(r'\s+(bool|tristate|int|hex|string)\b',line)
        if current and match:types[current]=match[1]
        match=re.match(r'\s+default\s+(\S+)',line)
        if current and match and current not in values:values[current]=match[1]
    for line in (wlan/'configs/blair_gki_wlan_defconfig').read_text().splitlines():
        match=re.match(r'CONFIG_(\w+)=(.*)',line.strip())
        if match:values[match[1]]=match[2]
    definitions, overrides = [], []
    for name,value in sorted(values.items()):
        kind=types.get(name,'bool')
        if kind in ('bool','tristate') or value in ('y','n','m'):
            if value=='y':
                definitions.append('#define CONFIG_'+name+' 1')
                overrides.append('CONFIG_'+name+'=y')
        else:
            definition=json.dumps(value.strip(chr(34))) if kind=='string' else value
            definitions.append('#define CONFIG_'+name+' '+definition)
            if not name.startswith(('WLAN_CTRL_NAME','ROME_IF')):overrides.append('CONFIG_'+name+'='+value)
    dest.mkdir(parents=True,exist_ok=True)
    (dest/'autoconf.h').write_text('\n'.join(definitions)+'\n')
    (dest/'overrides.txt').write_text(' '.join(overrides)+'\n')
    probes=[]
    for name,needle,macro in FEATURES:
        p=kernel/name
        if p.is_file() and needle in p.read_text(errors='replace'):probes.append('#define '+macro+' (1)')
    (dest/'grep_defines.h').write_text('\n'.join(probes)+'\n')
