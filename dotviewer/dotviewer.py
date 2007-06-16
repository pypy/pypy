#! /usr/bin/env python
"""
Command-line interface for a dot file viewer.

    dotviewer.py filename.dot
    dotviewer.py filename.plain
    dotviewer.py --server [interface:]port

In the first form, show the graph contained in a .dot file.
In the second form, the graph was already compiled to a .plain file.
In the third form, listen for connexion on the given port and display
the graphs sent by the remote side.
"""

import sys

def main(args = sys.argv[1:]):
    import getopt
    options, args = getopt.getopt(args, 's:h', ['server=', 'help'])
    server_addr = None
    for option, value in options:
        if option in ('-h', '--help'):
            print >> sys.stderr, __doc__
            sys.exit(2)
        if option in ('-s', '--server'):
            server_addr = value
    if not args and server_addr is None:
        print >> sys.stderr, __doc__
        sys.exit(2)
    for filename in args:
        import graphclient
        graphclient.display_dot_file(filename)
    if server_addr is not None:
        import graphserver
        graphserver.listen_server(server_addr)

if __name__ == '__main__':
    main()
