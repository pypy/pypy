import sys
import traceback
import time
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

# some generic stuff to make working with BaseHTTPServer a bit nicer...

# XXX note that this has some overlap with pypy/translator/js/lib/server.py,
# and should perhaps at some point be merged... (the main reason why I started
# this instead of using server.py is because the latter is mostly geared
# towards some tricks (transparent AJAX), and doesn't utilize or abstract the
# HTTP support in a very clean way, hopefully I can find a model here to
# improve server.py)

# XXX this needs to be built using httplib.responses in Python > 2.5 :(
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

class Handler(BaseHTTPRequestHandler):
    """ BaseHTTPRequestHandler that does object publishing
    """

    application = None # attach web root (Collection object) here!!
    bufsize = 1024
    
    def do_GET(self, send_body=True):
        """ perform a request """
        path, query = self.process_path(self.path)
        try:
            resource = self.find_resource(path, query)
            headers, data = resource(self, path, query)
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
        else:
            status = 200
            if not 'content-type' in [k.lower() for k in headers]:
                headers['Content-Type'] = 'text/html; charset=UTF-8'
        headers['Connection'] = 'close' # for now? :|
        self.response(status, headers, data, send_body)

    do_POST = do_GET

    def do_HEAD(self):
        return self.do_GET(False)

    def process_path(self, path):
        """ split the path in a path and a query part

            returns a tuple (path, query), where path is a string and
            query a dictionary containing the GET vars (URL decoded and such)
        """
        path = path.split('?')
        if len(path) > 2:
            raise ValueError('illegal path %s' % (path,))
        p = path[0]
        q = len(path) > 1 and path[1] or ''
        return p, q

    def find_resource(self, path, query):
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
        headers = {'Content-Type': 'text/plain',
                   }
        headers.update(get_nocache_headers())
        if e.status in [301, 302]:
            headers['Location'] = e.data
            body = 'Redirecting to %s' % (e.data,)
        else:
            body = 'Error: %s (%s)' % (e.status, e.message)
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

def run_server(address, handler):
    """ run a BaseHTTPServer instance
    """
    server = HTTPServer(address, handler)
    server.serve_forever()

def get_nocache_headers():
    return {'Connection': 'close',
            'Pragma': 'no-cache',
            'Expires': 'Mon, 26 Jul 1997 05:00:00 GMT',
            'Last-Modified': time.strftime("%a, %d %b %Y %H:%M:%S GMT"),
            'Cache-Control': 'no-cache, must-revalidate',
            'Cache-Control': 'post-check=0, pre-check=0',
            }

# ready-to-use Collection and resource implementations
class FsFile(object):
    exposed = True
    debug = False
    def __init__(self, path, content_type):
        self._path = path
        self._content_type = content_type

    _data = None
    def __call__(self, handler, path, query):
        if self._data is None or self.debug:
            self._data = self._path.read()
        # XXX should handle caching here...
        return ({'Content-Type': self._content_type}, self._data)

