#!/usr/bin/python
import logging

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

from ble_helper import (
    BLUEZ_SERVICE_NAME,
    DBUS_PROP_IFACE,
    LE_ADVERTISING_MANAGER_IFACE,
    LE_ADVERTISEMENT_IFACE,
    InvalidArgsException,
    ID_MANUFACTURE,
    UUID_BEACONSERVICE_SHORT,
    UUID_CONFIGSERVICE_SHORT,
    find_adapter_path,
)

logger = logging.getLogger('BLELogger')


class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/advertisement'

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.manufacturer_data = None
        self.timeout = None
        self.duration = None
        self.service_uuids = None
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type

        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary(
                self.manufacturer_data, signature='qv')
        if self.timeout is not None:
            properties['Timeout'] = dbus.UInt16(self.timeout)
        if self.duration is not None:
            properties['Duration'] = dbus.UInt16(self.duration)
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids,
                                                    signature='s')
        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_duration(self, duration):
        self.duration = duration

    def add_timeout(self, timeout):
        self.timeout = timeout

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dbus.Dictionary({}, signature='qv')
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature='y')

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def get_all(self, interface):
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE,
                         in_signature='',
                         out_signature='')
    def release(self):
        print('%s: Released!' % self.path)

    def __del__(self):
        logger.info("Advertisement object released!({})".format(self._locations))
        if len(self._locations):
            self.remove_from_connection()


class ConfigAdvertisement(Advertisement):
    def __init__(self, bus, index, freq=5, timeout=0):
        Advertisement.__init__(self, bus, index, 'peripheral')
        # Advertisement.__init__(self, bus, index, 'broadcast')
        # type = broadcast is not supported by pi
        self.add_service_uuid(UUID_CONFIGSERVICE_SHORT)
        manufacture_id = ID_MANUFACTURE
        self.add_manufacturer_data(manufacture_id, [0xff])
        if timeout:
            self.add_timeout(timeout)
        self.add_duration(freq)


class BeaconAdvertisement(Advertisement):
    def __init__(self, bus, index, key, timeout=0):
        Advertisement.__init__(self, bus, index, 'peripheral')
        # Advertisement.__init__(self, bus, index, 'broadcast')
        # type = broadcast is not supported by pi
        self.add_service_uuid(UUID_BEACONSERVICE_SHORT)
        manufacture_id = ID_MANUFACTURE
        pkt_index = [index]
        # pktData = [i for i in range(0, 22)]
        pkt_data = list(key)
        self.add_manufacturer_data(manufacture_id, pkt_index + pkt_data)
        if timeout:
            self.add_timeout(timeout)
        self.add_duration(3)
        # self.add_duration(10)


class ConfigCtrl:
    def __init__(self, mainloop, bus):
        self.mainloop = mainloop
        adapter_path = find_adapter_path(bus, [LE_ADVERTISING_MANAGER_IFACE])
        self.manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
            LE_ADVERTISING_MANAGER_IFACE)
        self.config_adv = ConfigAdvertisement(bus, index=4, freq=30)
        self.registered = False

    def register_ad_cb(self):
        logger.info('Advertisement registered')

    def register_ad_error_cb(self, error):
        logger.info('Failed to register advertisement: ' + str(error))
        self.mainloop.quit()

    def start(self):
        if self.registered:
            logger.warning("ConfigCtrl already started!")
            return
        logger.info('ConfigCtrl Started!')
        self.registered = True
        self.manager.RegisterAdvertisement(
            self.config_adv.get_path(), {},
            reply_handler=self.register_ad_cb,
            error_handler=self.register_ad_error_cb)

    def stop(self):
        if not self.registered:
            print("ConfigCtrl not running!")
            return
        self.registered = False
        self.manager.UnregisterAdvertisement(self.config_adv)
        logger.info('Advertisement unregistered')

    def __del__(self):
        logger.info('configAdv object released!({})'.format(self.config_adv._locations))
        if self.registered:
            self.stop()
        if len(self.config_adv._locations):
            self.config_adv.remove_from_connection()
        # self.config_adv.__del__()


class BeaconCtrl():
    def __init__(self, mainloop, bus, key):
        self.mainloop = mainloop
        adapter_path = find_adapter_path(bus, [LE_ADVERTISING_MANAGER_IFACE])
        # adapter_props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
        #                            DBUS_PROP_IFACE)
        # adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))

        self.manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
            LE_ADVERTISING_MANAGER_IFACE)
        self.registered = False
        self.beacon_adv = []
        for i in range(1, 4):
            if i == 3:
                self.beacon_adv.append(
                    BeaconAdvertisement(
                        bus, i,
                        key[44:] + 0xFFFF.to_bytes(2, byteorder='little')))
            else:
                self.beacon_adv.append(
                    BeaconAdvertisement(bus, i, key[(i - 1) * 22:i * 22]))

    def register_ad_cb(self):
        logger.info('Advertisement registered')
        # for a in self.beacon_adv:
        # 	Log('debug','path,location: ({},{})'.format(a._object_path,a._locations))

    def register_ad_error_cb(self, error):
        logger.info('Failed to register advertisement: ' + str(error))
        self.mainloop.quit()

    def start(self):
        if self.registered:
            logger.warning("BeaconCtrl already started!")
            return
        logger.info("BeaconCtrl started!")
        self.registered = True
        for i in range(0, 3):
            self.manager.RegisterAdvertisement(
                self.beacon_adv[i].get_path(), {},
                reply_handler=self.register_ad_cb,
                error_handler=self.register_ad_error_cb)

    def stop(self):
        if not self.registered:
            logger.warning("BeaconCtrl not running!")
            return
        self.registered = False
        for i in range(0, 3):
            self.manager.UnregisterAdvertisement(self.beacon_adv[i])
        logger.info('Advertisement unregistered')

    def __del__(self):
        logger.info('beaconAdv object released!({})'.format(
            [a._locations for a in self.beacon_adv]))
        if self.registered:
            self.stop()
        for a in self.beacon_adv:
            # Log('debug','before releasing: ({},{})'.format(a._object_path,a._locations))
            if len(a._locations):
                a.remove_from_connection()
            # Log('debug','after releasing: ({},{})'.format(a._object_path,a._locations))
            # a.__del__()
