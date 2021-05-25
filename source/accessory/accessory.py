import logging
import os.path

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
from gi.repository import GObject

import beacon
import gatt_server
import logger_config

global AccessoryKeyPath
AccessoryKeyPath = 'AccessoryKey'


def run():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    mainloop = GObject.MainLoop()
    bus = dbus.SystemBus()
    logger.info('Create GattServer Application')
    application = gatt_server.GattServerCtrl(mainloop, bus)
    application.start()
    timeout_id = 0
    # when finish writing, write cmd to trigger mainloop.quit()
    if not os.path.isfile(AccessoryKeyPath):
        adv = beacon.ConfigCtrl(mainloop, bus)
    else:
        with open(AccessoryKeyPath, 'rb') as f:
            key = f.read()
            f.close()
        adv = beacon.BeaconCtrl(mainloop, bus, key)
        timeout_id = GObject.timeout_add(5 * 60 * 1000, application.stop)
        logger.debug('timeout ID:{}'.format(timeout_id))
    adv.start()
    mainloop.run()
    if timeout_id:
        GObject.source_remove(timeout_id)


if __name__ == '__main__':
    logger_config.init_logger()
    global logger
    logger = logging.getLogger('BLELogger')
    try:
        while True:
            run()
    except KeyboardInterrupt:
        pass
