
""" This is example of totally basic server for XMLHttp request
built on top of BaseHTTPServer.

Construction is like that:

you take your own implementation of Handler and subclass it
to provide whatever you like. Each request is checked first for
apropriate method in handler (with dots replaced as _) and this method
needs to have set attribute exposed

If method is not there, we instead try to search exported_methods (attribute
of handler) for apropriate JSON call. We write down a JSON which we get as
a return value (note that right now arguments could be only strings) and
pass them to caller
"""

import traceback

HTTP_STATUS_MESSAGES = {
    200: 'OK',
    204: 'No Content',
    301: 'Moved permanently',
    302: 'Found',
    304: 'Not modified',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not found',
    500: 'Server error',
    501: 'Not implemented',
}

class HTTPError(Exception):
    """ raised on HTTP errors """
    def __init__(self, status, data=None):
        self.status = status
        self.message = HTTP_STATUS_MESSAGES[status]
        self.data = data

    def __str__(self):
        data = ''
        if self.data:
            data = ' (%s)' % (self.data,)
        return '<HTTPException %s "%s"%s>' % (self.status, self.message, data)

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

import re
import time
import random
import os
import sys

import py
from pypy.translator.js.lib.url import parse_url

from pypy.translator.js import json

from pypy.rpython.ootypesystem.bltregistry import MethodDesc, BasicExternal,\
    described
from pypy.translator.js.main import rpython2javascript
from pypy.translator.js import commproxy

commproxy.USE_MOCHIKIT = False

class Collection(object):
    """ an HTTP collection
    
        essentially this is a container object that has a path that ends on a
        slash, and support for PATH_INFO (so can have (virtual or not)
        children)

        children are callable attributes of ourselves that have an 'exposed'
        attribute themselves, that accept 3 arguments: 'handler', a reference
        to the BaseHTTPHandler that handles the request (XXX should be
        abstracted?), 'path', the requested path to the object, and 'query',
        the (unparsed!) GET query string (without a preceding ?)
    """

    def traverse(self, path, orgpath):
        """ traverse path relative to self

            'path' is the path requested by the client, split on '/', but
            relative from the current object: parent Collection items may have
            removed items (they will have, actually, unless 'self' is the root
            of the website) from the beginning on traversal to 'self'

            path is split on '/', the first item is removed and used to do
            a lookup on self, if that fails a 404 is raised, if successful
            the item is used to continue traversal (if the object found is
            a Collection type) or to handle the request (if the object found
            is a callable with .exposed set to True)

            if path equals '', a lookup for 'index' is done

            can be overridden in subclasses to implement different path
            handling (PATH_INFO-like stuff)
        """
        name = path.pop(0)
        if name == '':
            name = 'index'
        name = name.replace(".", "_")
        resource = getattr(self, name, None)
        if (resource is None or (not isinstance(resource, Collection) and
                (not callable(resource) or
                    not getattr(resource, 'exposed', True)))):
            raise HTTPError(404)
        if path:
            if not isinstance(resource, Collection):
                raise HTTPError(500) # no PATH_INFO allowed for non-Collection
            return resource.traverse(path, orgpath)
        else:
            if isinstance(resource, Collection):
                # targeting a collection directly: redirect to its 'index'
                raise HTTPError(301, orgpath + '/')
            if not getattr(resource, 'exposed', False):
                # don't reveal what is not accessible...
                raise HTTPError(404)
            return resource

class ExportedMethods(BasicExternal, Collection):
    _render_base_path = "exported_methods"
    def traverse(self, path, orgpath):
        """ traverse path relative to self

            'path' is the path requested by the client, split on '/', but
            relative from the current object: parent Collection items may have
            removed items (they will have, actually, unless 'self' is the root
            of the website) from the beginning on traversal to 'self'

            path is split on '/', the first item is removed and used to do
            a lookup on self, if that fails a 404 is raised, if successful
            the item is used to continue traversal (if the object found is
            a Collection type) or to handle the request (if the object found
            is a callable with .exposed set to True)

            if path equals '', a lookup for 'index' is done

            can be overridden in subclasses to implement different path
            handling (PATH_INFO-like stuff)
        """
        name = path.pop(0)
        name = name.replace(".", "_")
        resource = getattr(self, name, None)
        if not resource:
            raise HTTPError(404)
        return lambda **args : ('text/json', json.write(resource(**args)))
    _render_xmlhttp = True

exported_methods = ExportedMethods()

def patch_handler(handler_class):
    """ This function takes care of adding necessary
    attributed to Static objects
    """
    for name, value in handler_class.__dict__.iteritems():
        if isinstance(value, Static) and value.path is None:
            assert hasattr(handler_class, "static_dir")
            value.path = os.path.join(str(handler_class.static_dir),
                                      name + ".html")

class TestHandler(BaseHTTPRequestHandler):
    exported_methods = exported_methods
    
    def do_GET(self):
        path, args = parse_url(self.path)
        if not path:
            path = ["index"]
        name_path = path[0].replace(".", "_")
        if len(path) > 1:
            rest = os.path.sep.join(path[1:])
        else:
            rest = None
        method_to_call = getattr(self, name_path, None)
        if method_to_call is None or not getattr(method_to_call, 'exposed', None):
            exec_meth = getattr(self.exported_methods, name_path, None)
            if exec_meth is None:
                self.send_error(404, "File %s not found" % path)
            else:
                self.serve_data('text/json', json.write(exec_meth(**args)),
                                True)
        else:
            if rest:
                outp = method_to_call(rest, **args)
            else:
                outp = method_to_call(**args)
            if isinstance(outp, (str, unicode)):
                self.serve_data('text/html', outp)
            elif isinstance(outp, tuple):
                self.serve_data(*outp)
            else:
                raise ValueError("Don't know how to serve %s" % (outp,))

    def log_message(self, format, *args):
        # XXX just discard it
        pass
    
    do_POST = do_GET
    
    def serve_data(self, content_type, data, nocache=False):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Content-length", len(data))
        if nocache:
            self.send_nocache_headers()
        self.end_headers()
        self.wfile.write(data)

    def send_nocache_headers(self):
        self.send_header('Expires', 'Mon, 26 Jul 1997 05:00:00 GMT')
        self.send_header('Last-Modified',
                         time.strftime("%a, %d %b %Y %H:%M:%S GMT"))
        self.send_header('Cache-Control', 'no-cache, must-revalidate')
        self.send_header('Cache-Control', 'post-check=0, pre-check=0')
        self.send_header('Pragma', 'no-cache')

class Static(object):
    exposed = True
    
    def __init__(self, path=None):
        self.path = path

    def __call__(self):
        return open(str(self.path)).read()

class FsFile(object):
    exposed = True
    debug = False
    def __init__(self, path, content_type="text/html"):
        self._path = path
        self._content_type = content_type

    _data = None
    def __call__(self):
        if self._data is None or self.debug:
            self._data = self._path.read()
        return ({'Content-Type': self._content_type}, self._data)

class StaticDir(Collection):
    exposed = True

    def __init__(self, path, type=None):
        self.path = path
        self.type = type

    def traverse(self, path, orgpath):
        data = open(os.path.join(str(self.path), *path)).read()
        if self.type:
            return lambda : (self.type, data)
        return lambda : data

def create_server(server_address = ('', 8000), handler=TestHandler,
                 server=HTTPServer):
    """ Parameters:
    spawn - create new thread and return (by default it doesn't return)
    fork - do a real fork
    timeout - kill process after X seconds (actually doesn't work for threads)
    port_file - function to be called with port number
    """
    patch_handler(handler)
    httpd = server(server_address, handler)
    httpd.last_activity = time.time()
    print "Server started, listening on %s:%s" %\
          (httpd.server_address[0],httpd.server_port)
    return httpd

def start_server_in_new_thread(server):
    import thread
    thread.start_new_thread(server.serve_forever, ())

def start_server_in_new_process(server, timeout=None):
    pid = os.fork()
    if not pid:
        if timeout:
            def f(httpd):
                while 1:
                    time.sleep(.3)
                    if time.time() - httpd.last_activity > timeout:
                        httpd.server_close()
                        import os
                        os.kill(os.getpid(), 15)
            import thread
            thread.start_new_thread(f, (server,))

        server.serve_forever()
        os._exit(0)
    return pid

Handler = TestHandler
# deprecate TestHandler name

class NewHandler(BaseHTTPRequestHandler):
    """ BaseHTTPRequestHandler that does object publishing
    """

    application = None # attach web root (Collection object) here!!
    bufsize = 1024

    def do_GET(self, send_body=True):
        """ perform a request """
        path, query = self.process_path(self.path)
        _, args = parse_url("?" + query)
        try:
            resource = self.find_resource(path)
            # XXX strange hack
            if hasattr(resource, 'im_self'):
                resource.im_self.server = self.server
            retval = resource(**args)
            if isinstance(retval, str):
                headers = {'Content-Type': 'text/html'}
                data = retval
            else:
                headers, data = retval
                if isinstance(headers, str):
                    headers = {'Content-Type': headers}
        except HTTPError, e:
            status = e.status
            headers, data = self.process_http_error(e)
        except:
            exc, e, tb = sys.exc_info()
            tb_formatted = '\n'.join(traceback.format_tb(tb))
            status = 200
            data = 'An error has occurred: %s - %s\n\n%s' % (exc, e,
                                                             tb_formatted)
            headers = {'Content-Type': 'text/plain'}
            if hasattr(self.application, 'handle_error'):
                self.application.handle_error(exc, e, tb)
        else:
            status = 200
            if not 'content-type' in [k.lower() for k in headers]:
                headers['Content-Type'] = 'text/html; charset=UTF-8'
        self.response(status, headers, data, send_body)

    do_POST = do_GET

    def do_HEAD(self):
        return self.do_GET(False)

    def process_path(self, path):
        """ split the path in a path and a query part#
    
            returns a tuple (path, query), where path is a string and
            query a dictionary containing the GET vars (URL decoded and such)
        """
        path = path.split('?')
        if len(path) > 2:
            raise ValueError('illegal path %s' % (path,))
        p = path[0]
        q = len(path) > 1 and path[1] or ''
        return p, q

    def find_resource(self, path):
        """ find the resource for a given path
        """
        if not path:
            raise HTTPError(301, '/')
        assert path.startswith('/')
        chunks = path.split('/')
        chunks.pop(0) # empty item
        return self.application.traverse(chunks, path)

    def process_http_error(self, e):
        """ create the response body and headers for errors
        """
        headers = {'Content-Type': 'text/html'} # XXX need more headers here?
        if e.status in [301, 302]:
            headers['Location'] = e.data
            body = 'Redirecting to %s' % (e.data,)
        else:
            message, explain = self.responses[e.status]
            body = self.error_message_format % {'code': e.status, 'message': message,
                                                'explain': explain}
        return headers, body
    
    def response(self, status, headers, body, send_body=True):
        """ generate the HTTP response and send it to the client
        """
        self.send_response(status)
        if (isinstance(body, str) and
                not 'content-length' in [k.lower() for k in headers]):
            headers['Content-Length'] = len(body)
        for keyword, value in headers.iteritems():
            self.send_header(keyword, value)
        self.end_headers()
        if not send_body:
            return
        if isinstance(body, str):
            self.wfile.write(body)
        elif hasattr(body, 'read'):
            while 1:
                data = body.read(self.bufsize)
                if data == '':
                    break
                self.wfile.write(data)
        else:
            raise ValueError('body is not a plain string or file-like object')
