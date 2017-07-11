#!/usr/bin/python

import SocketServer
import subprocess

import translator

host = '0.0.0.0'


class CTFForwardHandler(SocketServer.BaseRequestHandler):
    allow_reuse_address = True

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

    def handle(self):
        self.request.send(
            'One line of token, please. If no token, send an empty line.\n'
            'Token:\n')
        token = ''
        while not token.endswith('\n'):
            token += self.request.recv(1)
        token = token.strip()
        tid = translator.translate(token)
        #oport = self.server.oport_base + tid
        self.request.send('ID = %d, Forwarding the request to sub server.\n' %
                          tid)
        socket_fd = self.request.fileno()
        p = subprocess.Popen(
            [
                'docker', 'exec', '-i', '-u', '233:233',
                self.server.docker_prefix + ('%03d' % tid), 'nc', '127.0.0.1',
                '2323'
            ],
            stdin=socket_fd,
            stdout=socket_fd)
        p.wait()


def forward_port(port, docker_prefix):
    server = SocketServer.ForkingTCPServer((host, port), CTFForwardHandler)
    server.docker_prefix = docker_prefix
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        raise


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print 'Usage: %s port docker_prefix' % sys.argv[0]
        exit(-1)
    port = int(sys.argv[1])
    docker_prefix = (sys.argv[2])
    forward_port(port, docker_prefix)
