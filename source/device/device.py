import argparse
import base64
import datetime
import logging
import queue
import time

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa

import config_app
import key_management
import logger_config
import scan


def GetLocation():
    return "Hello!".encode('utf-8')


def FormKey(key_bytes):
    e = 65537
    n = int.from_bytes(key_bytes, 'little')
    key_num = rsa.RSAPublicNumbers(e=e, n=n)
    pub_key = key_num.public_key(backend=default_backend())
    return pub_key


def Upload(dataJSON):
    url = "https://bletracker.supportvector.com/ble/register"
    r = requests.post(url, json=dataJSON)
    if r.status_code == 200 and r.json().get('code', -1) == 0:
        logger.info("Uploaded!")
    else:
        logger.info("Upload failed. {}".format(r.text))
    # if server_on:
    #     conn = http.client.HTTPConnection('localhost', 8888)
    #     conn.request('POST', '',
    #                  base64.b64encode(json.dumps(dataJSON).encode('utf-8')),
    #                  {})
    #     logger.info("Uploaded!")
    #     conn.close()
    # else:
    #     logger.info("(Fake)Uploaded to server")


class Accessory():
    def __init__(self, addr):
        self.addr = addr
        self.key = [[], [], []]
        self.last_seen = None

    def ResetKey(self):
        logger.debug('Reset Key!')
        self.key = [[], [], []]

    def RecordKey(self, index, key):
        assert index > 0 and index <= 3, "invalid key index:{}".format(index)
        if (len(self.key[index - 1]) == 0):
            # self.key[index - 1] = key
            if index == 3:
                self.key[index - 1] = key[:-2]
            else:
                self.key[index - 1] = key
            if self.KeyReady():
                self.UploadAcc()
        logger.debug("updated key:{}".format(self.key))

    def KeyReady(self):
        check_1 = (len(self.key[0]) == 22)
        check_2 = (len(self.key[1]) == 22)
        check_3 = (len(self.key[2]) == 20)
        return (check_1 and check_2 and check_3)

    def UploadAcc(self):
        # print("{} Found!".format(self.addr))
        location = GetLocation()
        pubkey_bytes = b''
        for i in range(3):
            pubkey_bytes += b''.join(self.key[i])
        logger.debug('{}'.format(pubkey_bytes))
        pubKey = FormKey(pubkey_bytes)
        # encrypted = base64.b64encode(pubKey.encrypt(location,padding.PKCS1v15()))
        encrypted = pubKey.encrypt(location, padding.PKCS1v15())
        for_upload = {
            'key': base64.b64encode(pubkey_bytes).decode('utf-8'),
            'content': base64.b64encode(encrypted).decode('utf-8')
        }
        logger.debug('\nkey:{},content:{}'.format(pubkey_bytes.hex(), encrypted.hex()))
        logger.debug('forUpload:{}'.format(for_upload))
        Upload(for_upload)


Accessories = []


# TODO: daily clean up on Acc list
def GotMessage(msg):
    # 	self.message.put({'type':'config',
    # 					'addr':address.encode('ascii', 'replace'),
    # 					'time':datetime.datetime.now()},block=True)
    # 	self.message.put({'type':'beacon',
    # 					'addr':address.encode('ascii', 'replace'),
    # 					'time':datetime.datetime.now(),
    # 					'index':int(v[0]),
    # 					'data':[bytes([d]) for d in v[1:23]]},block=True)
    logger.info("-- Got msg! \n{}".format(msg))
    for acc in Accessories:
        if acc.addr == msg['addr']:
            logger.info('acc:{} existed!'.format(acc.addr))
            acc.last_seen = msg['time']
            if msg['type'] == 'beacon':
                if acc.last_seen is None or \
                        ((msg['time'] - acc.last_seen) > datetime.timedelta(minutes=2)):
                    acc.ResetKey()
                acc.RecordKey(int(msg['index']), msg['data'])
            return
    acc = Accessory(msg['addr'])
    acc.last_seen = msg['time']
    if msg['type'] == 'beacon':
        acc.RecordKey(int(msg['index']), msg['data'])
    Accessories.append(acc)


def QueryAccessoryInfo(pub_key):
    url = "https://bletracker.supportvector.com/ble/query"
    r = requests.post(url, json={'key': base64.b64encode(pub_key).decode('utf-8')})
    # example response: {"code":0,"results":[{"content":"encrypted content","timestamp":1621498817959}]}
    if r.status_code != 200 or r.json().get('code', -1) != 0:
        logger.info("Query failed. {}".format(r.text))
        return
    results = r.json().get('results', [])
    # todo: decrypt and show results
    priKey = key_management.LoadPriKey()
    for result in results:
        decrypted = priKey.decrypt(base64.b64decode(result['content']), padding.PKCS1v15())
        logger.info('Decrypted result: {}'.format(decrypted))

    # # pubkey_bytes,e = key_management.ExtractPubKey()
    # conn = http.client.HTTPConnection('localhost', 8888)
    # conn.request('GET', '',base64.b64encode(pub_key),{})
    # response = conn.getresponse()
    # # print(base64.b64decode(response.read()))
    # conn.close()
    # priKey = key_management.LoadPriKey()
    # decrypted = priKey.decrypt(base64.b64decode(response.read()),padding.PKCS1v15())
    # logger.info('Decrypted result: {}'.format(decrypted))


if __name__ == '__main__':
    logger_config.init_logger()
    global logger
    logger = logging.getLogger('BLELogger')

    parser = argparse.ArgumentParser()
    parser.add_argument('--role', type=str,
                        choices=['scanner', 'owner-set', 'owner-find'],
                        required=True)
    parser.add_argument('--server', type=str,
                        choices=['on', 'off'],
                        default='off')
    args = parser.parse_args()
    role = args.role
    global server_on
    if args.server == 'on':
        server_on = True
    else:
        server_on = False
    logger.info('Mode: {}, ServerOn: {}'.format(role, server_on))

    # if (len(sys.argv) == 2) and (sys.argv[1] == 'owner'):
    #     logger.info('Owner Mode!')
    #     # global isOwnerConfig
    #     isOwnerConfig = True
    # else:
    #     logger.info('Scanner Mode!')
    #     isOwnerConfig = False
    if role == 'owner-find':
        if not server_on:
            logger.error('please config server on')
            exit()
        pubkey_bytes, e = key_management.ExtractPubKey()
        QueryAccessoryInfo(pubkey_bytes)
        exit()
    message_queue = queue.Queue(maxsize=100)
    scan_thread = scan.ScanProc(message_queue)
    scan_thread.start()
    if role == 'owner-set':
        config_thread = config_app.ConfigThread(Accessories)
        config_thread.start()
    try:
        while True:
            try:
                msg = message_queue.get(block=False)
                GotMessage(msg)
            except queue.Empty:
                time.sleep(8)
    except KeyboardInterrupt:
        scan_thread.stop()
        if role == 'owner-set':
            config_thread.stop()
