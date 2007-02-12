#!/usr/bin/env python
"""
In this example, we'll show how to add javascript to our simple
server from previous example
"""

from pypy.translator.js.lib import server
import sys

# here we have virtual script "source.js" which we generate
# on-the-fly when requested
HTML = """
<html>
<head>
  <script src="source.js"/>
  <title>pypy.js tutorial</title>
</head>
<body onload="show()">
</body>
</html>
"""

from pypy.translator.js.main import rpython2javascript
# here we import rpython -> javascript conversion utility

from pypy.translator.js.modules import dom
# and here we import functions from modules that we want to use

# this is function which will be translated into javascript,
# we can put it in a different module if we like so
def show():
    dom.alert("Alert")

class Handler(server.TestHandler):

    def index(self):
        return HTML
    index.exposed = True

    # here we generate javascript, this will be accessed when
    # asked for source.js
    def source_js(self):
        # this returns content-type (if not text/html)
        # and generated javascript code
        # None as argument means current module, while "show" is the
        # name of function to be exported (under same name)
        return "text/javascript", rpython2javascript(None, ["show"])
    source_js.exposed = True

# server start, same as before
if __name__ == '__main__':
    server.create_server(handler=Handler).serve_forever()
