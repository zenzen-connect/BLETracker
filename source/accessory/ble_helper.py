import logging

import dbus
import dbus.exceptions

logger = logging.getLogger('BLELogger')

# PATH
BLUEZ_SERVICE_NAME = 'org.bluez'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'

LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'

GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE = 'org.bluez.GattDescriptor1'


# EXCEPTION
class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'


class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotSupported'


class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotPermitted'


class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidValueLength'


class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.Failed'


# METHOD


def find_adapter_path(bus, pattern):
    om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = om.GetManagedObjects()
    for path, ifaces in objects.items():
        # print('checking adapter %s, keys: %s' % (path, ifaces.keys()))
        match_count = 0
        for p in pattern:
            if p in ifaces.keys():
                match_count += 1
        if match_count == len(pattern):
            return path
    raise Exception("Bluetooth adapter not found")


def reveal_dbus(bus):
    manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                             DBUS_OM_IFACE)
    objects = manager.GetManagedObjects()
    logger.debug('\n****Reveal Dbus Info:****')
    for path, interfaces in objects.items():
        logger.debug("\n - Path:{}".format(path))
        for i in interfaces.keys():
            logger.debug('\n --- Interface:{}; \n ----- Props:{}'.format(
                    i, interfaces[i]))


# UUID
ID_MANUFACTURE = 0x6B5A
UUID_BEACONSERVICE_SHORT = "361f"
UUID_BEACONSERVICE_WHOLE = '0000361f-0000-1000-8000-00805f9b34fb'
UUID_CONFIGSERVICE_SHORT = '361e'
UUID_CONFIGSERVICE_WHOLE = '0000361e-0000-1000-8000-00805f9b34fb'
UUID_CONFIGCHRC_SHORT = '361d'
UUID_CONFIGCHRC_WHOLE = '0000361d-0000-1000-8000-00805f9b34fb'
# Configurable
ADAPTER_INTERFACE = BLUEZ_SERVICE_NAME + '.Adapter1'
DEVICE_INTERFACE = BLUEZ_SERVICE_NAME + '.Device1'
