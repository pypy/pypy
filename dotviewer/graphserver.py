#! /usr/bin/env python
"""
Usage:
    graphserver.py [interface:]port
    dotviewer.py --server [interface:]port

Start a server listening for connexions on the given port.  The two ways
to start a server are equivalent.  The server displays the graphs sent
by a remote process.  On the remote process' side, set the GRAPHSERVER
environment variable to HOST:PORT.

Here is a step-by-step example on how to use it in combination with ssh
port forwarding (replace 9999 with a random port number of your choice,
e.g. between 8000 and 20000):

  - on your local machine, run:
        graphserver.py localhost:9999

  - connect to a remote machine, allowing the remote side to contact
    your local dotviewer:
        ssh -R9999:localhost:9999 machinename

  - set the $GRAPHSERVER env var on the remote machine to point to the
    redirected port (in bash):
        export GRAPHSERVER=:9999

  - then any graph-viewing command you execute while $GRAPHSERVER is set
    will reach your local dotviewer and basically appear to work
    completely transparently.

  - to automate steps 2 and 3, I've put the following entry in my local
    .ssh/config:
                    Host machinename
                        RemoteForward 9999 127.0.0.1:9999

    and I've added the 'export GRAPHSERVER=:9999' line to my .bashrc on
    the remote machine.
"""

import sys
import msgstruct
from cStringIO import StringIO


class Server(object):

    def __init__(self, io):
        self.io = io
        self.display = None

    def run(self, only_one_graph=False):
        # wait for the CMSG_INIT message
        msg = self.io.recvmsg()
        if msg[0] != msgstruct.CMSG_INIT or msg[1] != msgstruct.MAGIC:
            raise ValueError("bad MAGIC number")
        # process messages until we have a pygame display
        while self.display is None:
            self.process_next_message()
        # start a background thread to process further messages
        if not only_one_graph:
            import thread
            thread.start_new_thread(self.process_all_messages, ())
        # give control to pygame
        self.display.run1()

    def process_all_messages(self):
        try:
            while True:
                self.process_next_message()
        except EOFError:
            from drawgraph import display_async_quit
            display_async_quit()

    def process_next_message(self):
        msg = self.io.recvmsg()
        fn = self.MESSAGES.get(msg[0])
        if fn:
            fn(self, *msg[1:])
        else:
            self.log("unknown message code %r" % (msg[0],))

    def log(self, info):
        print >> sys.stderr, info

    def setlayout(self, layout):
        if self.display is None:
            # make the initial display
            from graphdisplay import GraphDisplay
            self.display = GraphDisplay(layout)
        else:
            # send an async command to the display running the main thread
            from drawgraph import display_async_cmd
            display_async_cmd(layout=layout)

    def cmsg_start_graph(self, graph_id, scale, width, height, *rest):
        from drawgraph import GraphLayout
        self.newlayout = GraphLayout(float(scale), float(width), float(height))

        def request_reload():
            self.io.sendmsg(msgstruct.MSG_RELOAD, graph_id)
        def request_followlink(word):
            self.io.sendmsg(msgstruct.MSG_FOLLOW_LINK, graph_id, word)

        self.newlayout.request_reload = request_reload
        self.newlayout.request_followlink = request_followlink

    def cmsg_add_node(self, *args):
        self.newlayout.add_node(*args)

    def cmsg_add_edge(self, *args):
        self.newlayout.add_edge(*args)

    def cmsg_add_link(self, word, *info):
        if len(info) == 1:
            info = info[0]
        elif len(info) >= 4:
            info = (info[0], info[1:4])
        self.newlayout.links[word] = info

    def cmsg_fixed_font(self, *rest):
        self.newlayout.fixedfont = True

    def cmsg_stop_graph(self, *rest):
        self.setlayout(self.newlayout)
        del self.newlayout
        self.io.sendmsg(msgstruct.MSG_OK)

    def cmsg_missing_link(self, *rest):
        self.setlayout(None)

    def cmsg_say(self, errmsg, *rest):
        from drawgraph import display_async_cmd
        display_async_cmd(say=errmsg)

    MESSAGES = {
        msgstruct.CMSG_START_GRAPH: cmsg_start_graph,
        msgstruct.CMSG_ADD_NODE:    cmsg_add_node,
        msgstruct.CMSG_ADD_EDGE:    cmsg_add_edge,
        msgstruct.CMSG_ADD_LINK:    cmsg_add_link,
        msgstruct.CMSG_FIXED_FONT:  cmsg_fixed_font,
        msgstruct.CMSG_STOP_GRAPH:  cmsg_stop_graph,
        msgstruct.CMSG_MISSING_LINK:cmsg_missing_link,
        msgstruct.CMSG_SAY:         cmsg_say,
        }


def listen_server(local_address):
    import socket, graphclient, thread
    if isinstance(local_address, str):
        if ':' in local_address:
            interface, port = local_address.split(':')
        else:
            interface, port = '', local_address
        local_address = interface, int(port)
    s1 = socket.socket()
    s1.bind(local_address)
    s1.listen(5)
    print 'listening on %r...' % (s1.getsockname(),)
    while True:
        conn, addr = s1.accept()
        print 'accepted connexion from %r' % (addr,)
        sock_io = msgstruct.SocketIO(conn)
        handler_io = graphclient.spawn_local_handler()
        thread.start_new_thread(copy_all, (sock_io, handler_io))
        thread.start_new_thread(copy_all, (handler_io, sock_io))
        del sock_io, handler_io, conn

def copy_all(io1, io2):
    try:
        while True:
            io2.sendall(io1.recv())
    except EOFError:
        io2.close_sending()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print >> sys.stderr, __doc__
        sys.exit(2)
    if sys.argv[1] == '--stdio':
        # a one-shot server running on stdin/stdout
        io = msgstruct.FileIO(sys.stdin, sys.stdout)
        srv = Server(io)
        try:
            srv.run()
        except Exception, e:
            import traceback
            f = StringIO()
            traceback.print_exc(file=f)
            # try to add some explanations
            help = (" | if you want to debug on a remote machine, see\n"
                    " | instructions in dotviewer/graphserver.py\n")
            try:
                import pygame
            except ImportError:
                f.seek(0)
                f.truncate()
                print >> f, "ImportError"
                print >> f, " | Pygame is not installed; either install it, or"
                print >> f, help
            else:
                if isinstance(e, pygame.error):
                    print >> f, help
            io.sendmsg(msgstruct.MSG_ERROR, f.getvalue())
    else:
        listen_server(sys.argv[1])
