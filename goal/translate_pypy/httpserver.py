from __future__ import generators
from __future__ import nested_scopes
import BaseHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
import urlparse, cgi, htmlentitydefs
import sys, os, time
from cStringIO import StringIO


class Translator:
    """For use with format strings.
    
    'formatstring % translator' will evaluate all %(xxx)s expressions
    found in the format string in the given globals/locals.

    Multiline expressions are assumed to be one or several complete
    statements; they are executed and whatever they print is inserted back
    into the format string."""
    
    def __init__(self, globals, locals):
        self.globals = globals
        self.locals = locals
    
    def __getitem__(self, expr):
        if '\n' in expr:
            if not expr.endswith('\n'):
                expr += '\n'
            prevstdout = sys.stdout
            try:
                sys.stdout = f = StringIO()
                exec expr in self.globals, self.locals
            finally:
                sys.stdout = prevstdout
            return f.getvalue()
        else:
            return eval(expr, self.globals, self.locals)

class TranslatorIO:
    "Lazy version of Translator."
    
    def __init__(self, fmt, d):
        self.gen = self.generate(fmt, d)
        
    def read(self, ignored=None):
        for text in self.gen:
            if text:
                return text
        return ''

    def close(self):
        self.gen = ()

    def generate(self, fmt, d):
        t = Translator(d, d)
        for data in fmt.split('\x0c'):
            yield data % t


# HTML quoting

text_to_html = {}
for key, value in htmlentitydefs.entitydefs.items():
    text_to_html[value] = '&' + key + ';'

def htmlquote(s):
    return ''.join([text_to_html.get(c, c) for c in s])


# HTTP Request Handler

pathloaders = {}

def canonicalpath(url):
    if url.startswith('/'):
        url = url[1:]
    return url.lower()

def register(url, loader):
    pathloaders[canonicalpath(url)] = loader

def is_registered(url):
    return canonicalpath(url) in pathloaders

def load(filename, mimetype=None, locals=None):
    if mimetype and mimetype.startswith('text/'):
        mode = 'r'
    else:
        mode = 'rb'
    f = open(filename, mode)
    if locals is not None:
        data = f.read()
        f.close()
        #data = data.replace('%"', '%%"')
        d = globals().copy()
        d.update(locals)
        f = TranslatorIO(data, d)
    return f, mimetype

def fileloader(filename, mimetype=None):
    def loader(**options):
        return load(filename, mimetype)
    return loader

class HTTPRequestError(Exception):
    pass

class MiniHandler(SimpleHTTPRequestHandler):

    def send_head(self, query=''):
        addr, host, path, query1, fragment = urlparse.urlsplit(self.path)
        path = canonicalpath(path)
        if path not in pathloaders:
            if path + '/' in pathloaders:
                return self.redirect(path + '/')
            self.send_error(404)
            return None
        kwds = {}
        for q in [query1, query]:
            if q:
                kwds.update(cgi.parse_qs(q))
        loader = pathloaders[path]
        try:
            hdr = self.headers
            hdr['remote host'] = self.client_address[0]
            f, ctype = loader(headers=hdr, **kwds)
        except IOError, e:
            self.send_error(404, "I/O error: " + str(e))
            return None
        except HTTPRequestError, e:
            self.send_error(500, str(e))
            return None
        except:
            f = StringIO()
            import traceback
            traceback.print_exc(file=f)
            data = htmlquote(f.getvalue())
            data = data.replace('\n', '<br>\n')
            self.send_error(500)
            return StringIO('<hr><p>'+data+'</p>')
        if ctype is None:
            ctype = self.guess_type(self.translate_path(self.path))
        elif f is None:
            return self.redirect(ctype)
        
        self.send_response(200)
        self.send_header("Content-type", ctype)
        self.end_headers()
        return f

    def redirect(self, url):
        self.send_response(302)
        self.send_header("Content-type", 'text/html')
        self.send_header("Location", url)
        self.end_headers()
        return StringIO('''<html><head></head><body>
Please <a href="%s">click here</a> to continue.
</body></html>
''' % url)

    def do_POST(self):
        try:
            nbytes = int(self.headers.getheader('content-length'))
        except:
            nbytes = 0
        query = self.rfile.read(nbytes).strip()
        f = self.send_head(query)
        if f:
            self.copyfile(f, self.wfile)
            f.close()


def my_host():
    import gamesrv
    port = gamesrv.socketports[gamesrv.openhttpsocket()]
    return '127.0.0.1:%d' % port
