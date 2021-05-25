import base64
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

# from cryptography.hazmat.backends import default_backend
# from cryptography.hazmat.primitives.asymmetric import rsa
# from cryptography.hazmat.primitives.asymmetric import padding
# from cryptography.hazmat.primitives import serialization

# def Decrypt(encryptedBytes):
# 	with open('../Device/priKey.pem', "rb") as f:
# 		private_key = serialization.load_pem_private_key(
# 			f.read(),
# 			password=None,
# 			backend=default_backend()
# 		)
# 		f.close()
# 	decrypted = private_key.decrypt(encryptedBytes,padding.PKCS1v15())
# 	print('decrypt result:{}'.format(decrypted))
accessories = {}


class Resquest(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def _html(self, message):
        content = f"<html><body><h1>{message}</h1></body></html>"
        return content.encode("utf8")

    def do_GET(self):
        self._set_headers()
        request_raw = self.rfile.read(int(self.headers['content-length']))
        print("accessories:{}".format(accessories))
        print("requested:{}".format(base64.b64decode(request_raw)))
        # self.wfile.write(self._html("hi!"))
        if base64.b64decode(request_raw) in accessories.keys():
            self.wfile.write(
                base64.b64encode(accessories[base64.b64decode(request_raw)]))
        else:
            self.wfile.write(base64.b64encode(bytes([0xFF])))

    def do_POST(self):
        request_raw = self.rfile.read(int(self.headers['content-length']))
        print("request_raw:{}".format(request_raw))
        data = json.loads(base64.b64decode(request_raw).decode('utf-8'))
        # print(request_raw)
        record = {
            'key': base64.b64decode(data['key'].encode('utf-8')),
            'content': base64.b64decode(data['content'].encode('utf-8'))
        }
        print(record)
        accessories.update({record['key']: record['content']})
        # Decrypt(record['content'])
        self.wfile.write(self._html("POST!"))


if __name__ == '__main__':
    host = ('localhost', 8888)
    server = HTTPServer(host, Resquest)
    print("listen at: {}".format(host))
    server.serve_forever()
