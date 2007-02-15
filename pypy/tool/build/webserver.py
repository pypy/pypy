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

class Resource(object):
    """ an HTTP resource
    
        essentially this is an object with a path that does not end on a slash,
        and no support for PATH_INFO
    """

    def handle(self, handler, path, query):
        """ handle a single request to self 
        
            returns a tuple (content_type, data) where data is either a string
            (non-unicode!) or a file-like object with a read() method that
            accepts an integer (size) argument
        """
        raise NotImplemented('abstract base class')

class Collection(Resource):
    """ an HTTP collection
    
        essentially this is a container object that has a path that ends on a
        slash, and support for PATH_INFO (so can have (virtual or not)
        children)
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
            is a Resource type)

            if path equals '', a lookup for 'index' is done

            can be overridden in subclasses to implement different path
            handling (PATH_INFO-like stuff)
        """
        name = path.pop(0)
        if name == '':
            name = 'index'
        resource = getattr(self, name, None)
        if resource is None or not isinstance(resource, Resource):
            raise HTTPError(404)
        if path:
            if not isinstance(resource, Collection):
                raise HTTPError(500) # no PATH_INFO allowed for non-Collection
            return resource.traverse(path, orgpath)
        else:
            if isinstance(resource, Collection):
                # targeting a collection directly: redirect to its 'index'
                raise HTTPError(301, orgpath + '/')
            return resource

class Handler(BaseHTTPRequestHandler):
    application = None # attach web root (Collection object) here!!
    bufsize = 1024
    
    def do_GET(self, send_body=True):
        """ perform a request """
        path, query = self.process_path(self.path)
        try:
            resource = self.find_resource(path, query)
            headers, data = resource.handle(self, path, query)
        except HTTPError, e:
            status = e.status
            headers, data = self.process_http_error(e)
        else:
            status = 200
            if not 'content-type' in [k.lower() for k in headers]:
                headers['Content-Type'] = 'text/html; charset=UTF-8'
        self.response(status, headers, data)

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
        headers = {'Content-Type': 'text/plain'} # XXX need more headers here?
        if e.status in [301, 302]:
            headers['Location'] = e.data
            body = 'Redirecting to %s' % (e.data,)
        else:
            body = 'Error: %s (%s)' % (e.status, e.message)
        return headers, body
    
    def response(self, status, headers, body):
        self.send_response(status)
        if (isinstance(body, str) and
                not 'content-length' in [k.lower() for k in headers]):
            headers['Content-Length'] = len(body)
        for keyword, value in headers.iteritems():
            self.send_header(keyword, value)
        self.end_headers()
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
    server = HTTPServer(address, handler)
    server.serve_forever()


