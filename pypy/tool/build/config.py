import py

# general settings, used by both server and client
server = 'johnnydebris.net'
port = 12321
path = ['/home/johnny/temp/pypy-dist'] 

# option definitions for the startcompile script
# for now we have them here, we should probably use pypy's config instead 
# though...
import sys
def _use_modules_callback(option, opt_str, value, parser):
    parser.values.use_modules = [m.strip() for m in value.split(',') 
                                    if m.strip()]

def _maxint_callback(option, opt_str, value, parser):
    parser.values.maxint = 2 ** (int(value) - 1) - 1

options = [
    (('-m', '--use-modules'), {'action': 'callback', 'type': 'string',
                                'callback': _use_modules_callback,
                                'dest': 'use_modules', 'default': [],
                                'help': 'select the modules you want to use'}),
    (('-i', '--maxint'), {'action': 'callback', 'callback': _maxint_callback,
                                'default': sys.maxint, 'dest': 'maxint',
                                'type': 'string',
                                'help': ('size of an int in bits (32/64, '
                                            'defaults to sys.maxint)')}),
    (('-b', '--byteorder'), {'action': 'store', 
                                'dest': 'byteorder', 'default': sys.byteorder,
                                'nargs': 1,
                                'help': ('byte order (little/big, defaults '
                                            'to sys.byteorder)')}),
]

# settings for the server
projectname = 'pypy'
buildpath = '/home/johnny/temp/pypy-dist/pypy/tool/build/builds'
mailhost = '127.0.0.1'
mailport = 25
mailfrom = 'johnny@johnnydebris.net'

# settings for the tests
testpath = [str(py.magic.autopath().dirpath().dirpath())] 

