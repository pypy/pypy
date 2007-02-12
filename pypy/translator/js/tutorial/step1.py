#!/usr/bin/env python
"""

This is simple all-in-one self-containing server,
which just shows almost-empty HTML page

"""

# here we import server, which is derivative of
# BaseHTTPServer from python standard library
from pypy.translator.js.lib import server

# We create handler, which will handle all our requests
class Handler(server.TestHandler):

    def index(self):
        # provide some html contents
        return "<html><head></head><body><p>Something</p></body></html>"
    # this line is necessary to make server show something,
    # otherwise method is considered private-only
    index.exposed = True

if __name__ == '__main__':
    # let's start our server,
    # this will create running server instance on port 8000 by default,
    # which will run until we press Control-C
    server.create_server(handler=Handler).serve_forever()
