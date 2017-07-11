#!/usr/bin/python

import sys, os, time
import cgi
import subprocess
import tempfile

import SocketServer
import subprocess

import translator


def http_packet(code, data):
    p = ''
    p += 'HTTP/1.0 %d\n' % (code)
    p += 'Connection: close\n'
    p += 'Content-Length: %d\n' % len(data)
    p += 'Content-Type: text/html\n'
    p += '\n'
    p += data
    return p


good_flag_response = '''
<html>
<head>
<title>Flag checker</title>
</head>
<body>
<h1>Congratulations!</h1>
%s
</body>
</html>
'''

bad_flag_response = '''
<html>
<head>
<title>Flag checker</title>
</head>
<body>
<h1>Sorry...</h1>
%s
</body>
</html>
'''

fake_flag = 'yellow{0123456789abcdef0123456789abcdef_I_wish_to_be_a_flaggie}'

hint_response = '''
<html>
<head>
<title>Flag checker</title>
</head>
<body>
<h1>Welcome</h1>
If you have a flag for this challenge, use our flag checker to check whether you have an authentic one.<br>
<h2>Example:</h2>
<a href="/flag/''' + fake_flag.encode('base64') + '">' + fake_flag + '''</a>
</body>
</html>
'''

host = '0.0.0.0'


class Misc1Handler(SocketServer.StreamRequestHandler):
    allow_reuse_address = True

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

    def handle(self):
        time.sleep(0.5)

        try:
            first_line = self.rfile.readline().split()
            assert first_line[0] == 'GET'
            assert len(first_line) >= 2
            request = first_line[1]
        except (EOFError, AssertionError, IndexError):
            print >> sys.stderr, 'Ill formed request:', first_line
            self.wfile.write(
                http_packet(400,
                            'The server does not understand your request.'))
            raise

        if request.startswith('/flag/'):
            reql = request.split('?')
            try:
                recv_flag = reql[0][6:].decode('base64')
            except:
                print >> sys.stderr, 'Ill formed request:', request
                self.wfile.write(http_packet(400, 'Flag format wrong.'))
                raise
            with tempfile.TemporaryFile() as tmpfin:
                with tempfile.TemporaryFile() as tmpfout:
                    tmpfin.write(recv_flag + '\n')
                    tmpfin.seek(0)
                    token = ''
                    if len(reql) > 1:
                        for l in reql[1].split('&'):
                            if l.startswith('token='):
                                token = l.split('=')[1]
                                break
                    tid = translator.translate(token)
                    fc_proc = subprocess.Popen(
                        [
                            'docker', 'exec', '-i', '-u', '233:233',
                            self.server.docker_prefix + ('%03d' % tid), 'nc',
                            '127.0.0.1', '2323'
                        ],
                        stdin=tmpfin,
                        stdout=tmpfout)
                    time.sleep(1)
                    tmpfout.seek(0)
                    fc_response = tmpfout.read()
                    print >> sys.stderr, 'input: %s\noutput: %s' % (
                        recv_flag, fc_response)
                    fc_response = [
                        cgi.escape(repr(_)[1:-1])
                        for _ in fc_response.split('\n')
                    ]
                    fc_response = '<br>'.join(fc_response)
            if 'Right!' in fc_response:
                self.wfile.write(
                    http_packet(200, good_flag_response % fc_response))
            else:
                self.wfile.write(
                    http_packet(200, bad_flag_response % fc_response))
        else:
            self.wfile.write(http_packet(200, hint_response))


def server(port, docker_prefix):
    server = SocketServer.ForkingTCPServer((host, port), Misc1Handler)
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
    server(port, docker_prefix)
