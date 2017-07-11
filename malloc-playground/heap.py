#!/usr/bin/python -i

from pwn import *

r = process('./malloc', stderr=2)

gdb.attach(r)#, execute='python from libheap import *\n')

mem = []
m = []
ms = []
"""
#define PROT_READ       0x1             /* Page can be read.  */
#define PROT_WRITE      0x2             /* Page can be written.  */
#define PROT_EXEC       0x4             /* Page can be executed.  */
#define PROT_NONE       0x0             /* Page can not be accessed.  */
#define PROT_GROWSDOWN  0x01000000      /* Extend change to start of
                                           growsdown vma (mprotect only).  */
#define PROT_GROWSUP    0x02000000      /* Extend change to start of
                                           growsup vma (mprotect only).  */

/* Sharing types (must choose one and only one of these).  */
#define MAP_SHARED      0x01            /* Share changes.  */
#define MAP_PRIVATE     0x02            /* Changes are private.  */
#ifdef __USE_MISC
# define MAP_TYPE       0x0f            /* Mask for type of mapping.  */
#endif

/* Other flags.  */
#define MAP_FIXED       0x10            /* Interpret addr exactly.  */
#ifdef __USE_MISC
# define MAP_FILE       0
# ifdef __MAP_ANONYMOUS
#  define MAP_ANONYMOUS __MAP_ANONYMOUS /* Don't use a file.  */
# else
#  define MAP_ANONYMOUS 0x20            /* Don't use a file.  */
# endif
# define MAP_ANON       MAP_ANONYMOUS
/* When MAP_HUGETLB is set bits [26:31] encode the log2 of the huge page size.
*/
# define MAP_HUGE_SHIFT 26
# define MAP_HUGE_MASK  0x3f
#endif
"""


def maps():
    with open('/proc/%d/maps' % proc.pidof(r)[0], 'rb') as f:
        print f.read()


def mmap(addr, length, prot, flags, fd, offset):
    r.sendline('mmap %ld %ld %ld %ld %ld %ld' %
               (addr, length, prot, flags, fd, offset))
    r.recvuntil('mmap return: ')
    return int(r.recvline()[2:].strip(), 16)


def minfo():
    r.sendline('minfo')
    return r.recvuntil('====\n')[:-5]


def leak():
    r.sendline('leak')
    return r.recvuntil('====\n')[:-5]


def list_mem():
    r.sendline('list')
    return r.recvuntil('====\n')[:-5]


def update_mem():
    global mem
    global m
    global ms
    tmp = [_.split(' ') for _ in list_mem().split('\n') if _ != '']
    mem = [(int(_[1], 16), int(_[2], 16)) for _ in tmp]
    m = [_[0] for _ in mem]
    ms = [_[1] for _ in mem]


ud = update_mem


def blind_malloc(size, ID):
    r.sendline('malloc %d %d' % (size, ID))


def malloc(size, ID=-1):
    if (ID == -1):
        update_mem()
        ID = len(mem)

    r.sendline('malloc %d %d' % (size, ID))
    update_mem()
    print 'malloc:', ID, hex(m[ID])
    #update_mem()


def calloc(size, ID=-1):
    if (ID == -1):
        update_mem()
        ID = len(mem)

    r.sendline('calloc %d %d' % (size, ID))
    update_mem()
    print 'calloc:', ID, hex(m[ID])

    #update_mem()


def realloc(addr, size, ID=-1):
    if (ID == -1):
        update_mem()
        ID = len(mem)

    r.sendline('realloc %d %d %d' % (addr, size, ID))
    update_mem()
    print 'realloc:', hex(addr), '->', ID, hex(m[ID])


def fopen(filename, mode='rb', ID=-1):
    if (ID == -1):
        update_mem()
        ID = len(mem)

    r.sendline('fopen %s %s %d' % (filename, mode, ID))
    update_mem()
    print 'fopen (', filename, ',', mode, ') ->', ID, hex(m[ID])


def fclose(addr):
    if (addr < 0x400000): addr = m[addr]
    r.sendline('fclose %d' % (addr))
    print 'fclose:', hex(addr)

    #update_mem()


def free(addr):
    if (addr < 0x400000): addr = m[addr]
    r.sendline('free %d' % (addr))
    print 'free:', hex(addr)


def dump(addr, elem_count, sizeID='q'):
    assert (sizeID in ['b', 'w', 'd', 'q'])
    r.sendline('dump %s %d %d' % (sizeID, addr, elem_count))
    return r.recvuntil('====\n')[:-5]


def write(addr, val, sizeID='q'):
    assert (sizeID in ['b', 'w', 'd', 'q'])
    r.sendline('write %s %d %d' % (sizeID, addr, val))


def ls():
    update_mem()
    print list_mem()


def d(addr, cnt=16):
    def escape_to(s, into='.'):
        return ''.join([(_ if ord(_) in range(32, 127) else into) for _ in s])

    rcv = dump(addr, cnt).split('\n')
    for i in range((cnt + 1) / 2):
        rr = rcv[i].split(' ')
        print '\x1b[1;33m%s\x1b[21;39m' % hex(
            addr + 16 * i), rr[0], rr[1], escape_to(rr[0].decode('hex')[::-1] +
                                                    rr[1].decode('hex')[::-1])

        #print '\x1b[1;32m%s\x1b[21;39m' % hex(addr + 16 * i), escape_to(rr[
        #    0].decode('hex')[::-1] + rr[1].decode('hex')[::-1])


def lk():
    print leak()


def info():
    print minfo()


l = ls
w = write
"""
for i in range(8):
    malloc(0x300 + i * 16, i)
list_mem()
for i in range(8, 16):
    malloc(0x300 + i * 16, i)

list_mem()
for i in range(16, 24):
    malloc(0x300 + i * 16, i)
update_mem()
for line in mem:
    print hex(line[0]), line[1]
"""
#tmp = [_.split(' ') for _ in list_mem().split('\n') if _ != '']
#print [(_[1], _[2]) for _ in tmp]

#print mem_status

#r.interactive()
