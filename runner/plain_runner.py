#!/usr/bin/python

import sys, os
import time
import subprocess
"""

The code here is too messy, since it is not modulized.

Now I explain why the tool is used. The tool will provide advantageous
debugging assistence with:
    a) customizable init gdb script. With the functionality, I can now
    have my variable to be the base of the main executable, libc, heap,
    etc.
    b) customizable execute method, aka configuration of libc and some
    ASLR pattern. You can change libc real time (not much attractive right?)
    and you can make the connection to have some trait with ASLR (such
    as making libc address to be 0x7fxxxx000000, which is in 1/4096
    chance by natural). When you socat this script, you can configure
    it to bruteforce about the executable, and filter out the "good"
    memory layout and make it to be the very service that take effect
    (although the default script here require your exploit to wait before
    good ASLR is present, after which the exp can send payload)
    The ASLR related code is commented by me, but you can use it under
    extreme cases.

"""

# The most often modified variables

# bruteforce arguments, you may set it to lower value if your PC detests.

MAX_TRIAL = 65536
MAX_CONCURRENT = 256

# On graphic linux if GDB_POPWINDOW is set, every connection will pop a
# terminal for one gdb
# If you use ssh to debug, you can set it to be false, in order to make
# gdb appear on the very terminal as socat. (but a sad story, you cannot
# send interrupt to gdb using ^C in this case)

GDB_POPWINDOW = True  #False

# If the program runs with a heap (heap is initiated before first input),
# check it to be true, otherwise, false.

# However it now only affect the module for bruteforcing aslr.

hasHeap = True
hasLibc = True

# x86-64 or x86-32 deprecated

#is64 = False

# fuzzing mode or exploiting mode
# fuzzing mode will stop debugger on discovering heap vulnerability
# although it might be not so useful as we have professional fuzzer

Fuzzing = False

# argv of the server

argv = ['./overwatch']

# if you have your custom libc in the same directory, this config is useful
# else, edit them to your preference

cwd = os.getcwd() + '/'

filename = argv[0]

libc = cwd + 'libc.so.6'

env = {'LD_PRELOAD': libc, 'PATH': '/bin:/usr/bin'}

custom_exec = ''

# ###### Run our real program, or if you like an ASLR-filtered version

#p = subprocess.Popen(argv, env=env)
p = subprocess.Popen(argv)

# below are generator for a good pattern of ASLR. You can also use the
# getaslrs function below!
'''
for i in range(MAX_TRIAL):
    if i % 16 == 0: print >> sys.stderr, 'Current attempt: %d' % i
    ps = []
    for j in range(MAX_CONCURRENT):
        ps.append(subprocess.Popen(argv, env=env))
    lucky_id = -1
    for j in range(MAX_CONCURRENT):
        while True:
            with open('/proc/%d/maps' % ps[j].pid, 'r') as f:
                aslr = f.readlines()
            libc_line = [_ for _ in aslr if 'libc.so' in _]
            if len(libc_line) > 0:
                break
            print >> sys.stderr, 'Missed target for %d, %d' % (i, j)
        libc_addr = int(libc_line[0].split()[0].split('-')[0], 16)
        #print >>sys.stderr, hex(libc_addr)
        if libc_addr == 0xf7558000:
            lucky_id = j
            break
    if lucky_id == -1:
        for p in ps:
            p.kill()
        del ps
    else:
        for j in range(MAX_CONCURRENT):
            if j != lucky_id:
                ps[j].kill()
        p = ps[lucky_id]
        break
'''

# end of <Run our real program>

# ###### Attach gdb (assume peda + libheap + glibc source are ready!!)

gdb_autoexec_filename = '.gdb_autoexec_script'

autoexec = '''
b abort
'''

def extract_addr(s):
    return int(s.split()[0].split('-')[0], 16)


def getaslr(aslr, signiture):
    filter_arr = [_ for _ in aslr if signiture in _]
    if len(filter_arr) == 0:
        return 0
    return extract_addr(filter_arr[0])


def getaslrs(p, retry=True, hasHeap=True, hasLibc=True):
    # main, stack, vdso, libc, heap
    hases = [True, True, True, hasLibc, hasHeap]
    sigs = [argv[0][2:], '[stack]', '[vdso]', 'libc', '[heap]']
    while True:
        with open('/proc/%d/maps' % p.pid, 'r') as f:
            aslr = f.readlines()
        addrs = []
        for i in range(len(sigs)):
            s = sigs[i]
            addr = getaslr(aslr, s)
            if not addr and hases[i]:
                print >> sys.stderr, 'Failed to get aslr of %s' % s
                if retry:
                    print >> sys.stderr, 'Retrying.'
                    time.sleep(1e-1)
                    break
                else:
                    return None
            else:
                addrs.append(addr)
        if len(addrs) == len(sigs):
            return addrs


#aslr = getaslrs(p, hasHeap=hasHeap, hasLibc=hasLibc)

autoexec += custom_exec

with open(cwd + gdb_autoexec_filename, 'w') as f:
    f.write(autoexec + '\n')

gdb_term_argv = [
    '/usr/bin/x-terminal-emulator', '-e', 'gdb-multiarch -q  "%s" %d -x "%s"' %
    (cwd + filename, p.pid, cwd + gdb_autoexec_filename)
]

if GDB_POPWINDOW:
    gdb_p = subprocess.Popen(
        gdb_term_argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
else:
    gdb_p = subprocess.Popen(
        ['/bin/sh', '-c'] + gdb_term_argv[2:], stdin=2, stdout=2)

# end of <Attach gdb>

# following will preventing the ghost connection of the program consuming the cpu

#effective_p = subprocess.Popen(['nc', '0', '9345'])

import signal
import sys


def signal_handler(signal, frame):
    print >> sys.stderr, 'Python killed'
    p.kill()
    exit(-1)


signal.signal(signal.SIGPIPE, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# wait for the program to die

p.wait()
