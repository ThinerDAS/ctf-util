#!/usr/bin/python

from Crypto.Cipher import AES

key = '10b2eaddc9fc8b90e33cd91c7061ca80'.decode('hex')

max_range = 1#0

cipher = AES.new(key, AES.MODE_ECB)


def translate(token):
    # invalid token will be 0
    if len(token) != 32:
        return 0
    for c in token:
        if c not in '0123456789abcdef':
            return 0
    dec = cipher.decrypt(token.decode('hex'))
    tid = int(dec.encode('hex'), 16)
    if tid >= max_range:
        tid = 0
    return tid


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3 or sys.argv[1] not in ['enc', 'dec']:
        print 'Usage: %s [enc|dec] [tid|token]' % sys.argv[0]
        exit(-1)
    mode = sys.argv[1]
    arg = sys.argv[2]
    if mode == 'enc':
        tid = int(arg)
        if tid < 0 or tid >= max_range:
            print 'tid invalid: tid should be in the range of [%d, %d)' % (
                0, max_range)
            exit(-1)
        enc = cipher.encrypt(hex(int(arg))[2:].rjust(32, '0').decode('hex'))
        print 'token:', enc.encode('hex')
    else:
        print 'tid:', translate(arg)
