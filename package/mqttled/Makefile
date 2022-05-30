
include $(TOPDIR)/rules.mk

PKG_NAME:=mqttled
PKG_VERSION:=0.1
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/trevortrevor/mqttled.git
PKG_SOURCE_VERSION:=6691bbdc2713f561691dcd06b3b1459aa60f6d36

PKG_MAINTAINER:=Tom Grime <tom.grime@gmail.com>
PKG_LICENSE:=MIT
PKG_LICENSE_FILES:=LICENSE

include $(INCLUDE_DIR)/package.mk
include ../../lang/python/python3-package.mk

define Package/mqttled
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=LED Control from MQTT 
  URL:=https://github.com/trevortrevor/mqttled/
  DEPENDS:= \
	+python3-light \
    +python3-paho-mqtt \
	+python3-asyncio \
	+python3-uci \
	+python3-logging \
	+python3-idna \
	+python3-setuptools \
endef

define Package/mqttled/description
	Exposes the LEDs of your device to an MQTT broker with optional Homeassistant auto discovery
endef

define Py3Package/mqttled/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(CP) $(PKG_INSTALL_DIR)/usr/bin/* $(1)/usr/bin/

	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./files/mqttled.init $(1)/etc/init.d/mqttled
	$(INSTALL_DATA) ./files/mqttled $(1)/etc/config/mqttled
endef

define Package/mqttled/conffiles
/etc/config/mqttled
endef

$(eval $(call Py3Package,mqttled))
$(eval $(call BuildPackage,mqttled))
