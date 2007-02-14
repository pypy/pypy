#!/usr/bin/env python

""" the mandatory guestbook example

    accompanies the pypyp/doc/js/webapps_with_pypy.txt document, serves as
    a simple example to show how to go about writing a pypy web application
"""

import autopath

from pypy.translator.js.lib import server
from pypy.translator.js.lib.support import callback
from pypy.translator.js.main import rpython2javascript

import py
import shelve

class ExportedMethods(server.ExportedMethods):
    """ this provides the methods that are exposed to the client ('AJAX' stuff)
    """
    def __init__(self):
        super(ExportedMethods, self).__init__()
        self._db = shelve.open('messages')
        self._db.setdefault('messages', [])

    # callback makes that a method gets exposed, it can get 2 arguments,
    # 'ret' for specifying the return value, and 'args' for specifying the
    # argument types
    @callback(retval=[str])
    def get_messages(self):
        return self._db['messages']

    @callback(retval=str)
    def add_message(self, name='', message=''):
        text = '%s says: %s' % (name, message)
        m = self._db['messages']
        m.append(text)
        self._db['messages'] = m
        return text

exported_methods = ExportedMethods()

FUNCTION_LIST = ['init_guestbook', 'add_message']
def guestbook_client():
    """ compile the rpython guestbook_client code to js
    """
    import guestbook_client
    return rpython2javascript(guestbook_client, FUNCTION_LIST)

class Handler(server.Handler):
    """ a BaseHTTPRequestHandler subclass providing the HTTP methods
    """
    # provide the exported methods
    exported_methods = exported_methods

    # a simple html page
    def index(self):
        html = """
            <html>
              <head>
                <title>Guestbook</title>
                <script type="text/javascript" src="/guestbook.js"></script>
              </head>
              <body onload="init_guestbook()">
                <h2>Guestbook</h2>
                <div id="messages">
                  <!-- this will be filled from javascript -->
                </div>
                <form action="." method="post"
                      onsubmit="add_message(this); return false">
                  name: <input type="text" name="name" id="name" /><br />
                  message:<br />
                  <textarea name="message" id="message"></textarea><br />
                  <input type="submit" />
                </form>
              </body>
            </html>
        """
        return 'text/html', html
    index.exposed = True

    # the (generated) javascript
    def guestbook_js(self):
        if hasattr(self.server, 'source'):
            source = self.server.source
        else:
            source = guestbook_client()
            self.server.source = source
        return "text/javascript", source
    guestbook_js.exposed = True

if __name__ == '__main__':
    addr = ('', 8008)
    httpd = server.create_server(server_address=addr, handler=Handler)
    httpd.serve_forever()
