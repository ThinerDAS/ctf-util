#!/usr/bin/python

import signal

import sys,os

#import threading
import multiprocessing

import docker

import forwardserver
import misc1server

import translator

cwd=os.getcwd()

libc_path_root = cwd+'/../../libc-collection'
main_exe_root = cwd+'/..'

libc_mount_path = '/lib64'
main_mount_path = '/home/player'

default_server = forwardserver.forward_port

iport_base = 2300
#oport_base = 9000
max_range = translator.max_range

deploy_args = [
    {
        'name': 'moderate-pwn1',
        'exec': 'note_yellow',
        'libc': 'libc6_2.24-9_amd64',
        'cmd': 'LD_LIBRARY_PATH=/lib64 %s',
        'server': default_server,
    },
    {
        'name': 'moderate-pwn2',
        'exec': 'tmengine',
        'libc': 'libc6_2.24-9_amd64',
        'cmd': 'LD_LIBRARY_PATH=/lib64 %s',
        'server': default_server,
    },
    {
        'name': 'misc1',
        'exec': 'fc',
        'libc': 'libc6_2.24-9_amd64',
        'cmd': 'LD_LIBRARY_PATH=/lib64 LIBC_FATAL_STDERR_=1 %s 2>&1',
        'server': misc1server.server,
    },
    {
        'name': 'misc2',
        'exec': 'note_mys',
        'libc': 'glibc-2.25.90-1.fc27.x86_64',
        'cmd': '%s',
        'server': default_server,
    },
    {
        'name': 'beginner-pwn1',
        'exec': 'answert0univers3',
        'libc': 'glibc-2.24-4.fc25.x86_64',
        'cmd': '%s',
        'server': default_server,
    },
    {
        'name': 'beginner-pwn2',
        'exec': 'execver',
        'libc': 'glibc-2.24-3.fc25.x86_64',
        'cmd': '%s',
        'server': default_server,
    },
]

processes = []

containers = []

docker_cli = docker.from_env()


def deploy():
    print >> sys.stderr, 'Starting deployment'
    for i in range(len(deploy_args)):
        arg = deploy_args[i]
        name = arg['name']
        libc = arg['libc']
        cmd_tmpl = arg['cmd']
        executable = arg['exec']
        main_exe_path = main_exe_root + '/' + name
        libc_path = libc_path_root + '/' + libc + '/lib64'
        exec_docker_path = main_mount_path + '/' + executable
        # docker
        print >> sys.stderr, 'Starting dockers for %s' % name
        for j in range(max_range):
            print >> sys.stderr, 'Starting docker %d' % j
            ct = docker_cli.containers.run(
                image='busybox',
                command=[
                    'nc', '-ll', '-p', '2323', '-e', 'sh', '-c',
                    '(cat;pkill -9 -P $$)|(%s;pkill -9 -P $$)' %
                    (cmd_tmpl % exec_docker_path)
                ],
                volumes={
                    main_exe_path: {
                        'bind': main_mount_path,
                        'mode': 'ro'
                    },
                    libc_path: {
                        'bind': libc_mount_path,
                        'mode': 'ro'
                    },
                },
                #ports={2323: oport_base + i * max_range + j},
                working_dir=main_mount_path,
                name='CTF_subserver%03d-%03d' % (i, j),
                user=1000,#232,
                detach=True,
                #remove=True,
                restart_policy={'name': 'on-failure',
                                'MaximumRetryCount': 5},
                # security
                pids_limit=256,
                network_mode='none',
                oom_kill_disable=False,
                mem_limit='256M',
                mem_swappiness=0,
                cpu_shares=10,
                security_opt=['no-new-privileges'],
                ulimits=[{
                    'name': 'core',
                    'value': 0
                }, ],
                device_read_bps=[{
                    'Path': '/dev/sda',
                    'Rate': 0x100000
                }],
                device_write_bps=[{
                    'Path': '/dev/sda',
                    'Rate': 0x100000
                }])
            containers.append(ct)
        # forwarding server
        iport = iport_base + i
        #oport = oport_base + i * max_range
        print >> sys.stderr, 'Starting forward server for %s, port %d' % (
            name, iport)
        p = multiprocessing.Process(
            target=arg['server'], args=(iport, 'CTF_subserver%03d-' % i))
        processes.append(p)
        p.start()
    print >> sys.stderr, 'Waiting'
    signal.pause()


def destroy_deploy():
    print >> sys.stderr, 'Gracefully Exiting'
    for ct in containers:
        print >> sys.stderr, 'Removing', ct.name
        ct.remove(force=True)


if __name__ == '__main__':
    try:
        deploy()
    finally:
        destroy_deploy()
