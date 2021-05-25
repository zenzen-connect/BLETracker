#!/usr/bin/env python3
import datetime
import logging
import threading
import time

import dbus
from gi.repository import GObject

import key_management
from ble_helper import (
    BLUEZ_SERVICE_NAME,
    DBUS_OM_IFACE,
    DBUS_PROP_IFACE,
    DEVICE_INTERFACE,
    GATT_SERVICE_IFACE,
    GATT_CHRC_IFACE,
    UUID_CONFIGCHRC_WHOLE,
)

logger = logging.getLogger('BLELogger')

# check status every 4 packets,
# 16bytes data per packet (20 bytes per PDU)
class GattClient():
    def __init__(self, mainloop, bus):
        self.mainloop = mainloop
        self.bus = bus
        self.registered = False
        self.chrcs = None
        self.chrcs_path = None
        # RevealDbus(self.bus)
        manager = dbus.Interface(self.bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                                 DBUS_OM_IFACE)
        manager.connect_to_signal('InterfacesRemoved',
                                  self.interfaces_removed_cb)
        # manager.connect_to_signal('InterfacesAdded', self.interfaces_added_cb)
        retry_count = 5
        while retry_count:
            objects = manager.GetManagedObjects()
            chrcs_name = []
            for path, interfaces in objects.items():
                if GATT_CHRC_IFACE not in interfaces.keys():
                    continue
                chrcs_name.append(path)
                logger.debug("characteristics: {}".format(path))
            for path, interfaces in objects.items():
                if GATT_SERVICE_IFACE not in interfaces.keys():
                    continue
                chrc_paths = [d for d in chrcs_name if d.startswith(path + "/")]
                logger.debug("service:{},chrc:{}".format(path, chrc_paths))
                self._GetChrcs(path, chrc_paths)
            if self.chrcs is None:
                retry_count -= 1
                time.sleep(1)
            else:
                self.packet_startfrom = 0
                self.transfer_Round = 0
                self.key_data, e = key_management.ExtractPubKey()
                return
        self.generic_error_cb('Can not find GATT Chrcs')

    def _GetChrcs(self, service_path, chrc_paths):
        # service = bus.get_object(BLUEZ_SERVICE_NAME, servicePath)
        # serviceProps = service.GetAll(GATT_SERVICE_IFACE,
        #                            dbus_interface=DBUS_PROP_IFACE)
        for chrc_path in chrc_paths:
            chrc = self.bus.get_object(BLUEZ_SERVICE_NAME, chrc_path)
            chrc_props = chrc.get_all(GATT_CHRC_IFACE,
                                      dbus_interface=DBUS_PROP_IFACE)
            uuid = chrc_props['UUID']
            if uuid == UUID_CONFIGCHRC_WHOLE:
                logger.info("UUID_CONFIGCHRC added")
                self.chrcs = chrc
                self.chrcs_path = chrc_path
            else:
                logger.warning('Unrecognized characteristic: ' + uuid)
        return True

    def generic_error_cb(self, error):
        print('D-Bus call failed: ' + str(error))
        self.mainloop.quit()

    def interfaces_removed_cb(self, object_path, interfaces):
        if self.chrcs is None:
            return
        if object_path == self.chrcs_path:
            print('GATT Chrcs was removed')
            self.mainloop.quit()

    def CheckStatus(self, value):
        # print(value)
        received_pkt = int(int(value[1]) / 16)
        logger.info('{} Bytes transferred'.format(int(value[1])))
        if received_pkt == 4:
            logger.info('data transfer finish')
            self.mainloop.quit()
        else:
            if self.transfer_round == 4:
                logger.error('Fail to write key!')
                self.generic_error_cb('fail to write!')
            else:
                self.transfer_round += 1
                self.packet_startfrom = received_pkt
                self.WriteKeyData()

    def WriteKeyData(self):
        # for i in range(self.packet_startfrom,4):
        # 	data += (bytes([0,i*16,255,16]) + self.key_data[(i-1)*16:i*16])
        if self.packet_startfrom < 4:
            offset = self.packet_startfrom * 16
            data = offset.to_bytes(2, byteorder='little') + bytes(
                [255, 16]) + self.key_data[offset:offset + 16]
            self.packet_startfrom += 1
            logger.info('Write {} bytes'.format(len(data)))
            self.chrcs.WriteValue(
                data,
                {},
                reply_handler=self.WriteKeyData,
                error_handler=self.generic_error_cb,
                dbus_interface=GATT_CHRC_IFACE)
        else:
            self.chrcs.ReadValue({},
                                 reply_handler=self.CheckStatus,
                                 error_handler=self.generic_error_cb,
                                 dbus_interface=GATT_CHRC_IFACE)
    def start(self):
        if self.registered:
            logger.warning("GattClientCtrl already started!")
            return
        self.registered = True
        if self.chrcs is None:
            logger.error('no valid chrcs!!')
            self.generic_error_cb('no valid chrcs!!')
            return
        self.WriteKeyData()
        # self.chrcs.ReadValue({},reply_handler = self.revealContent,
        # 							error_handler=self.generic_error_cb,
        #                             dbus_interface=GATT_CHRC_IFACE)
        # self.chrcs.WriteValue(int(1500).to_bytes(2, byteorder='little'),{},
        # 							reply_handler = self.writeContent,
        # 							error_handler=self.generic_error_cb,
        #                             dbus_interface=GATT_CHRC_IFACE)

    def stop(self):
        if not self.registered:
            logger.warning("GattClientCtrl not running!")
            return
        self.registered = False
        # self.manager.UnregisterApplication(self.application)
        
    def __del__(self):
        if self.registered:
            self.stop()
        # dbus.service.Object.remove_from_connection(self.application)


def SelectDevice(Accessories):
    for acc in Accessories:
        if (acc.last_seen -
                datetime.datetime.now()) < datetime.timedelta(minutes=1):
            return acc.addr
    return None

def GetDevice(bus, addr):
    manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, "/"),
                             DBUS_OM_IFACE)
    objects = manager.GetManagedObjects()
    for path, ifaces in objects.items():
        device = ifaces.get(DEVICE_INTERFACE)
        if device is None:
            continue
        if (device["Address"] == addr):
            obj = bus.get_object(BLUEZ_SERVICE_NAME, path)
            return dbus.Interface(obj, DEVICE_INTERFACE)
    logger.error('no device found')


class ConfigThread(threading.Thread):
    
    def __init__(self, Accessories):
        self.Accessories = Accessories
        self.mainloop = None
        self.gattClient = None
        self._stop = False
        super().__init__()

    def run(self):
        logger.info('Hello Config Thread!')
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        self.mainloop = GObject.MainLoop()
        # while (SelectDevice(self.Accessories) is None):
        while True:
            logger.debug('Accessory Num:{}'.format(len(self.Accessories)))
            addr = SelectDevice(self.Accessories)
            if addr is not None:
                break
            time.sleep(5)
            if self._stop:
                return
        device = GetDevice(bus, addr)
        logger.info('Trying connect to {}'.format(addr))
        device.Connect()
        # device.ConnectProfile(UUID_CONFIGSERVICE_WHOLE)
        while True:
            path = device.object_path
            props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, path),
                                   DBUS_PROP_IFACE)
            sta = props.Get(DEVICE_INTERFACE, 'Connected')
            logger.debug('connect flag:{}'.format(sta))
            if sta:
                break
            time.sleep(1)
            if self._stop:
                return
        self.gattClient = GattClient(self.mainloop, bus)
        self.gattClient.start()
        logger.info('mainloop run')
        self.mainloop.run()
        logger.debug('mainloop end')
        device.Disconnect()
        logger.info("ConfigThread Ended!")

    def stop(self):
        self.mainloop.quit()
        logger.info("ConfigThread Stopped!")
