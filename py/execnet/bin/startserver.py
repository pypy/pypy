#! /usr/bin/env python

"""
    start socket based minimal readline exec server 
"""
# this part of the program only executes on the server side
#

progname = 'socket_readline_exec_server-1.2'
debug = 0 

import sys, socket, os

if debug: #  and not os.isatty(sys.stdin.fileno()): 
    f = open('/tmp/execnet-socket-pyout.log', 'a', 0) 
    old = sys.stdout, sys.stderr 
    sys.stdout = sys.stderr = f 

def execloop(serversock): 
    while 1: 
        try:
            print progname, 'Entering Accept loop', serversock.getsockname()
            clientsock,address = serversock.accept()
            print progname, 'got new connection from %s %s' % address
            clientfile = clientsock.makefile('r+b',0)
            print "reading line"
            source = clientfile.readline()
            clientfile.close()
            g = {'clientsock' : clientsock, 'address' : address}
            source = eval(source) 
            if not source:
                break 
            co = compile(source+'\n', source, 'exec')
            print progname, 'compiled source, executing' 
            try:
                exec co in g
            finally: 
                print progname, 'finished executing code' 
        except (SystemExit, KeyboardInterrupt):
            break 
        #except:
        #    import traceback
        #    traceback.print_exc()

def bind_and_listen(hostport):
    if isinstance(hostport, str):
        host, port = hostport.split(':')
        hostport = (host, int(port))
    serversock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversock.bind(hostport)
    serversock.listen(5)
    return serversock

def startserver(serversock):
    try:
        execloop(serversock)
    finally:
        print "leaving socketserver execloop"
        serversock.shutdown(2) 

if __name__ == '__main__':
    import sys
    if len(sys.argv)>1:
        hostport = sys.argv[1]
    else:
        hostport = ':8888'
    serversock = bind_and_listen(hostport) 
    startserver(serversock)

