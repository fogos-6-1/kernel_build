# SPDX-License-Identifier: GPL-2.0-only
DATAIPADRVTOP := $(DATAIPA_ROOT)/drivers/platform/msm
LINUXINCLUDE += -include $(DATAIPA_ROOT)/config/dataipa_vendor.h \
 -I$(DATAIPADRVTOP)/include -I$(DATAIPADRVTOP)/include/linux \
 -I$(DATAIPADRVTOP)/include/uapi -I$(DATAIPADRVTOP)/gsi \
 -I$(DATAIPADRVTOP)/gsi/gsihal -I$(DATAIPADRVTOP)/ipa \
 -I$(DATAIPADRVTOP)/ipa/ipa_v3 -I$(DATAIPADRVTOP)/ipa/ipa_v3/ipahal \
 -I$(DATAIPADRVTOP)/ipa/ipa_clients -I$(DATAIPADRVTOP)/ipa/ipa_v3/dump \
 -I$(DATAIPADRVTOP)/ipa/ipa_v3/dump/ipa5.5 -I$(RMNET_MEM_ROOT)
KBUILD_CPPFLAGS += -DCONFIG_IPA_RMNET_MEM=y \
 -DGSI_TRACE_INCLUDE_PATH=$(DATAIPADRVTOP)/gsi \
 -DIPA_TRACE_INCLUDE_PATH=$(DATAIPADRVTOP)/ipa/ipa_v3 \
 -DRNDIS_TRACE_INCLUDE_PATH=$(DATAIPADRVTOP)/ipa/ipa_clients
obj-m += gsi/ ipa/
