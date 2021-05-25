#!/usr/bin/python
import datetime
import logging
import threading

import dbus
import dbus.mainloop.glib
from gi.repository import GObject

from ble_helper import (
    BLUEZ_SERVICE_NAME,
    DBUS_OM_IFACE,
    DBUS_PROP_IFACE,
    ADAPTER_INTERFACE,
    DEVICE_INTERFACE,
    UUID_BEACONSERVICE_WHOLE,
    UUID_CONFIGSERVICE_WHOLE,
    FindAdapterPath,
)

logger = logging.getLogger('BLELogger')

class ScanCtrl():

    def __init__(self, mainloop, bus, message):
        self.mainloop = mainloop
        self.message = message
        adapter_path = FindAdapterPath(bus, [ADAPTER_INTERFACE])
        self.adapter = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, adapter_path), ADAPTER_INTERFACE)
        # adapter_props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
        #                            DBUS_PROP_IFACE)
        # adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))
        self.received_num = 0
        self.devices = {}
        self.registered = False

        bus.add_signal_receiver(self.InterfaceAdded,
                                dbus_interface=DBUS_OM_IFACE,
                                signal_name="InterfacesAdded")

        bus.add_signal_receiver(self.PropertiesChanged,
                                dbus_interface=DBUS_PROP_IFACE,
                                signal_name="PropertiesChanged",
                                arg0=DEVICE_INTERFACE,
                                path_keyword="path")

        manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                                 DBUS_OM_IFACE)
        objects = manager.GetManagedObjects()
        for path, interfaces in objects.items():
            if DEVICE_INTERFACE in interfaces.keys():
                self.devices[path] = interfaces[DEVICE_INTERFACE]

        self.adapter.SetDiscoveryFilter({
            'DuplicateData':
            False,
            'Transport':
            'le',
            'UUIDs': [UUID_BEACONSERVICE_WHOLE, UUID_CONFIGSERVICE_WHOLE]
        })

    def InterfaceAdded(self, path, interfaces):
        if DEVICE_INTERFACE not in interfaces.keys():
            logger.warning('InterfaceAdded key missed:{}'.format(interfaces.keys()))
            return
        properties = interfaces[DEVICE_INTERFACE]
        if not properties:
            logger.warning('properties empty!')
            return

        if path in self.devices:
            self.devices[path].update(properties)
        else:
            self.devices[path] = properties

        if "Address" in self.devices[path]:
            address = properties["Address"]
        else:
            address = "<unknown>"
        self.RevealData(address, path)

    def PropertiesChanged(self, interface, changed, invalidated, path):
        if interface != "org.bluez.Device1":
            logger.warning('Interface missed')
            return
        if path in self.devices:
            self.devices[path].update(changed)
        else:
            self.devices[path] = changed

        if "Address" in self.devices[path]:
            address = self.devices[path]["Address"]
        else:
            address = "<unknown>"
        self.RevealData(address, path)

    def RevealData(self, address, path):
        self.received_num += 1
        logger.debug("\n***{} : {} *** [ ".format(
                datetime.datetime.now().strftime("%H:%M:%S"), self.received_num)
            + address + " ]")
        properties = self.devices[path]
        content = properties['ManufacturerData']
        for k, v in content.items():
            logger.debug("manufacture_ID:{}".format(hex(k)))
            assert k == int(0x6b5a), "wrong manufacture_ID:{}".format(k)
            index = int(v[0])
            logger.debug("Index:{}".format(index))
            if (index == 255):
                self.message.put(
                    {
                        'type': 'config',
                        'addr': address,
                        'time': datetime.datetime.now()
                    },
                    block=True)
            else:
                self.message.put(
                    {
                        'type': 'beacon',
                        'addr': address,
                        'time': datetime.datetime.now(),
                        'index': int(v[0]),
                        'data': [bytes([d]) for d in v[1:23]]
                    },
                    block=True)
        
    def start(self):
        if self.registered:
            print("ScanCtrl already started!")
            return
        self.registered = True
        self.adapter.StartDiscovery()

    def stop(self):
        if not self.registered:
            print("ScanCtrl not running!")
            return
        self.registered = False
        self.adapter.StopDiscovery()
        print('Advertisement unregistered')
        logger.info("Stop Discovery!")

    def __del__(self):
        if self.registered:
            self.stop()


class ScanProc(threading.Thread):
    def __init__(self, message):
        self.mainloop = None
        self.scan = None
        self.message = message
        super().__init__()

    def run(self):
        logger.info("Hello ScanProc!")
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        self.mainloop = GObject.MainLoop()
        self.scan = ScanCtrl(self.mainloop, bus, self.message)
        self.scan.start()
        self.mainloop.run()

    def stop(self):
        logger.info('Byebye ScanProc!')
        self.scan.stop()
        self.mainloop.quit()


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    mainloop = GObject.MainLoop()
    scan = ScanCtrl(mainloop, bus)
    try:
        print('CTRL-C to stop')
        scan.start()
        mainloop.run()
    except KeyboardInterrupt:
        scan.stop()
        mainloop.quit()
