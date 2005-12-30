import py
import exceptions

ISOLATE = """
import sys
import imp

mod = channel.receive()
if isinstance(mod, str):
    mod = __import__(mod, {}, {}, ['__doc__'])
else:
    dir, name = mod
    file, pathname, description = imp.find_module(name, [dir])
    try:
        mod = imp.load_module(name, file, pathname, description)
    finally:
        if file:
            file.close()    
channel.send("loaded")
while True:
    func, args = channel.receive()
    try:
        res = getattr(mod, func)(*args)
    except KeyboardInterrupt:
        raise
    except:
        exc_type = sys.exc_info()[0] 
        channel.send(('exc', (exc_type.__module__, exc_type.__name__)))
    else:
        channel.send(('ok', res))
"""

class IsolateException(Exception):
    pass

class IsolateInvoker(object):
    # to have a nice repr
    
    def __init__(self, isolate, name):
        self.isolate = isolate
        self.name = name

    def __call__(self, *args):
        return self.isolate._invoke(self.name, args)
        
    def __repr__(self):
        return "<invoker for %r . %r>" % (self.isolate.module, self.name)

class Isolate(object):
    """
    Isolate lets load a module in a different process,
    and support invoking functions from it passing and
    returning simple values

    module: a dotted module name or a tuple (directory, module-name)
    """
    _closed = False

    def __init__(self, module):
        self.gw = py.execnet.PopenGateway()
        chan = self.chan = self.gw.remote_exec(ISOLATE)
        chan.send(module)
        assert chan.receive() == "loaded"

    def __getattr__(self, name):
        return IsolateInvoker(self, name)

    def _invoke(self, func, args):
        self.chan.send((func, args))
        status, value =  self.chan.receive()
        if status == 'ok':
            return value
        else:
            exc_type_module, exc_type_name = value
            if exc_type_module == 'exceptions':
                raise getattr(exceptions, exc_type_name)
            else:
                raise IsolateException, "%s.%s" % value 

    def _close(self):
        if not self._closed:
            self.chan.close()
            self.gw.exit()
            self._closed = True

    def __del__(self):
        self._close()

def close_isolate(isolate):
    assert isinstance(isolate, Isolate)
    isolate._close()
