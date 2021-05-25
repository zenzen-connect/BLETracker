import base64

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa

PubKeyPath = 'pubKey.pem'
PriKeyPath = 'priKey.pem'
AccessoryKeyPath = '../Accessory/AccessoryKey'
# AccessoryKeyPath = 'AccessoryKey'


def GenKeyPair():
    key_pair = rsa.generate_private_key(public_exponent=65537,
                                          key_size=512,
                                          backend=default_backend())
    public_key = key_pair.public_key()

    private_pem = key_pair.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption())
    with open(PriKeyPath, 'wb') as f:
        f.write(private_pem)
        f.close()

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.Subjectpublic_keyInfo
        # 	format=serialization.PublicFormat.PKCS1
    )
    with open(PubKeyPath, 'wb') as f:
        f.write(public_pem)
        f.close()


def LoadPubKey():
    with open(PubKeyPath, "rb") as f:
        public_key = serialization.load_pem_public_key(
            f.read(), backend=default_backend())
        f.close()
    return public_key


def LoadPriKey():
    with open(PriKeyPath, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend())
        f.close()
    return private_key


def ExtractPubKey():
    pub_key = LoadPubKey()
    raw_key = pub_key.public_numbers()
    raw_key_n = raw_key.n
    raw_key_e = raw_key.e
    assert raw_key_n.bit_length() == 512
    key_bytes = raw_key_n.to_bytes(64, byteorder='little')
    return (key_bytes, raw_key_e)


def StoreAccessoryKey():
    key_bytes, e = ExtractPubKey()
    with open(AccessoryKeyPath, 'wb') as f:
        f.write(key_bytes)
        f.close()


def TestEncrypt():
    plain = b'Hello World!'
    public_key = LoadPubKey()
    encrypted = base64.b64encode(public_key.encrypt(plain, padding.PKCS1v15()))
    print('encrypted:{}'.format(encrypted))
    private_key = LoadPriKey()
    decrypted = private_key.decrypt(base64.b64decode(encrypted),
                                   padding.PKCS1v15())
    print('decrypt result:{}'.format(decrypted == plain))


def TestExtractKeyBytes():
    pub_key = LoadPubKey()
    ## get raw bytes of pub key
    raw_key = pub_key.public_numbers()
    raw_key_n = raw_key.n
    raw_key_e = raw_key.e
    assert raw_key_n.bit_length() == 512
    key_bytes = raw_key_n.to_bytes(64, byteorder='little')
    # print("raw pub_key:{}".format(base64.b64encode(keyBytes)))
    print('raw pubKey in Bytes:{}'.format(key_bytes.hex()))
    ## form pub key object
    # newKeyNum = rsa.RSAPublicNumbers(e=rawKey.e,n=rawKey.n)
    # n = int.from_bytes(keyBytes,'little')
    n = int.from_bytes(list(key_bytes), 'little')
    new_key_num = rsa.RSAPublicNumbers(e=raw_key.e, n=n)
    new_pub_key = new_key_num.public_key(backend=default_backend())
    # print(newPubKey)
    new_public_pem = new_pub_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    # print(newpublic_pem)
    with open(PubKeyPath, "rb") as f:
        ori_pub_key = f.read()
        f.close()
    print("TestExtractKeyBytes: {}".format(new_public_pem == ori_pub_key))


if __name__ == '__main__':
    GenKeyPair()
    # Test()
    # TestExtractKeyBytes()
    # StoreAccessoryKey()
