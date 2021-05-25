import logging

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

from accessory import AccessoryKeyPath
from ble_helper import (
    BLUEZ_SERVICE_NAME,
    DBUS_OM_IFACE,
    DBUS_PROP_IFACE,
    GATT_MANAGER_IFACE,
    GATT_SERVICE_IFACE,
    GATT_CHRC_IFACE,
    GATT_DESC_IFACE,
    InvalidArgsException,
    NotSupportedException,
    UUID_CONFIGSERVICE_SHORT,
    UUID_CONFIGCHRC_SHORT,
    find_adapter_path,
)

logger = logging.getLogger('BLELogger')


class Application(dbus.service.Object):

    def __init__(self, bus, mainloop):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(ConfiguringService(bus, 0, mainloop))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response

    def __del__(self):
        logger.info('Application released!({})'.format(
            [s._locations for s in self.services]))
        # self.remove_from_connection()
        for s in self.services:
            if len(s._locations):
                s.remove_from_connection()
                s.__del__()
                # don't know why service object will not be released automatically
                # still got ref?


class Service(dbus.service.Object):

    PATH_BASE = '/org/bluez/example/service'

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID':
                    self.uuid,
                'Primary':
                    self.primary,
                'Characteristics':
                    dbus.Array(self.get_characteristic_paths(), signature='o')
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_SERVICE_IFACE]

    def __del__(self):
        logger.info('Service released!({})'.format(
            [c._locations for c in self.characteristics]))
        # self.remove_from_connection()
        for c in self.characteristics:
            if len(c._locations):
                c.remove_from_connection()
                c.__del__()


class Characteristic(dbus.service.Object):
    """
	org.bluez.GattCharacteristic1 interface implementation
	"""

    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service':
                    self.service.get_path(),
                'UUID':
                    self.uuid,
                'Flags':
                    self.flags,
                'Descriptors':
                    dbus.Array(self.get_descriptor_paths(), signature='o')
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='a{sv}',
                         out_signature='ay')
    def ReadValue(self, options):
        print('Default ReadValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print('Default WriteValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        print('Default StartNotify called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        print('Default StopNotify called, returning error')
        raise NotSupportedException()

    @dbus.service.signal(DBUS_PROP_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

    def __del__(self):
        logger.info('Chrcs released!({})'.format(
            [d._locations for d in self.descriptors]))
        # self.remove_from_connection()
        for d in self.descriptors:
            d.remove_from_connection()


class Descriptor(dbus.service.Object):
    """
	org.bluez.GattDescriptor1 interface implementation
	"""

    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + '/desc' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_DESC_IFACE: {
                'Characteristic': self.chrc.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_DESC_IFACE]

    @dbus.service.method(GATT_DESC_IFACE,
                         in_signature='a{sv}',
                         out_signature='ay')
    def ReadValue(self, options):
        print('Default ReadValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_DESC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print('Default WriteValue called, returning error')
        raise NotSupportedException()


class ConfiguringService(Service):
    def __init__(self, bus, index, mainloop):
        Service.__init__(self, bus, index, UUID_CONFIGSERVICE_SHORT, True)
        self.add_characteristic(
            ConfiguringCharacteristic(bus, 0, self, mainloop))


class ConfiguringCharacteristic(Characteristic):
    def __init__(self, bus, index, service, mainloop):
        Characteristic.__init__(
            self,
            bus,
            index,
            UUID_CONFIGCHRC_SHORT,
            # ['read', 'write','notify'],
            ['read', 'write'],
            service)
        self.status = [0, 0]
        # [addr that waiting for, bytes received]
        self.data = []
        self.mainloop = mainloop

    def ReadValue(self, options):
        # Log('debug','Data Read')
        return self.status

    def WriteValue(self, value, options):
        # int.from_bytes([B1~B2],'little') - addr Offset in bytes
        # int.from_bytes([B3],'little') - Reserved
        # int.from_bytes([B4],'little') - Length in bytes
        # Log('debug','type:{}, received:{}'.format(type(value),value))
        value_bytes = b''.join([bytes([v]) for v in value])
        # convert from dbus.array to bytes
        offset = int.from_bytes(value_bytes[0:2], 'little')
        length = int.from_bytes(value_bytes[3:4], 'little')
        # value[3] will be convert to int directly.
        logger.info('received {} Bytes; offset:{},length:{}'.format(
            len(value_bytes), offset, length))
        assert length == 16, "length error:{}".format(length)
        if (offset == 0):
            logger.warning('Reset Data')
            self.status = [0, 0]
            self.data = b''
        if offset != self.status[0]:
            logger.warning('invalid offset')
            return
        self.data += value_bytes[4:]
        # Log('debug','data len:{}; source:{}'.format(len(self.data),value_bytes[4:]))
        self.status[0] = self.status[0] + length
        self.status[1] = self.status[1] + length
        if self.status[1] == 64:
            # 64 bytes key received!(512 bit)
            logger.info("{}Bytes received!".format(len(self.data)))
            with open(AccessoryKeyPath, 'wb') as f:
                logger.info('Key written to {}'.format(AccessoryKeyPath))
                f.write(self.data)
                f.close()
            self.mainloop.quit()
            logger.info('mainloop ended!')
        # self.data = value
        # Log('debug','{} Bytes Data Wrote'.format(len(self.data)))
        # Log('debug','Raw: {}'.format(self.data))


class GattServerCtrl():
    def __init__(self, mainloop, bus):
        self.mainloop = mainloop
        adapter_path = find_adapter_path(bus, [GATT_MANAGER_IFACE])
        self.manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
            GATT_MANAGER_IFACE)
        self.application = Application(bus, self.mainloop)
        self.registered = False

    def register_ad_cb(self):
        print('GATT application registered')

    def register_ad_error_cb(self, error):
        print('Failed to register application: ' + str(error))
        self.mainloop.quit()

    def start(self):
        if self.registered:
            logger.warning("GattServerCtrl already started!")
            return
        logger.info('GattServerCtrl started')
        self.registered = True
        self.manager.RegisterApplication(
            self.application.get_path(), {},
            reply_handler=self.register_ad_cb,
            error_handler=self.register_ad_error_cb)

    def stop(self):
        if not self.registered:
            logger.warning('GattServerCtrl not running!')
            return
        self.registered = False
        self.manager.UnregisterApplication(self.application)
        logger.info('Application unregistered')

    def __del__(self):
        logger.info('gattApp object removed!({})'.format(self.application._locations))
        if self.registered:
            self.stop()
        # dbus.service.Object.remove_from_connection(self.application)
        # Log('debug','before releasing: ({},{})'.format(self.application._object_path,self.application._locations))
        if len(self.application._locations):
            self.application.remove_from_connection()
        # Log('debug','after releasing: ({},{})'.format(self.application._object_path,self.application._locations))
