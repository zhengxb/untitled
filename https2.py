#!/usr/bin/env python

import socket, os
from SocketServer import BaseServer
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SimpleHTTPServer import SimpleHTTPRequestHandler
from OpenSSL import SSL

CERTIFICATE_PATH = os.getcwd() + '/CA/cacert.pem'
KEY_PATH = os.getcwd() + '/CA/private/key.pem'


class SecureHTTPServer(HTTPServer):
    def __init__(self, server_address, HandlerClass):
        BaseServer.__init__(self, server_address, HandlerClass)
        ctx = SSL.Context(SSL.SSLv23_METHOD)

        ctx.use_privatekey_file(KEY_PATH)
        ctx.use_certificate_file(CERTIFICATE_PATH)

        self.socket = SSL.Connection(ctx, socket.socket(self.address_family, self.socket_type))

        self.server_bind()
        self.server_activate()


class MemberUpdateHandler(SimpleHTTPRequestHandler):
    def setup(self):
        self.connection = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

    def do_GET(self):
        try:
            print 'path:', self.path
            print self.path.endswith('.txt')
            if self.path.endswith('.txt'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write("successful")
                return
            else:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write("not successful")
        except IOError:
            self.send_error(404, 'What you talking about willis?')


def test(HandlerClass=MemberUpdateHandler,
         ServerClass=SecureHTTPServer):
    server_address = ('', 4242)
    httpd = ServerClass(server_address, HandlerClass)
    sa = httpd.socket.getsockname()
    print "serving HTTPS on:", sa[0], "port:", sa[1], "..."
    httpd.serve_forever()


if __name__ == '__main__':
    test()