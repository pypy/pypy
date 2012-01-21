
from pypy.rlib.objectmodel import specialize

class AppBridgeCache(object):
    w__var = None
    w__std = None
    w_module = None

    def __init__(self, space):
        self.w_import = space.appexec([], """():
        def f():
           mod = __import__('numpypy.core._methods', {}, {}, [''])
           return mod
        return f
        """)
    
    @specialize.arg(2)
    def call_method(self, space, name, *args):
        w_meth = getattr(self, 'w_' + name)
        if w_meth is None:
            if self.w_module is None:
                self.w_module = space.call_function(self.w_import)
            w_meth = space.getattr(self.w_module, space.wrap(name))
            setattr(self, 'w_' + name, w_meth)
        return space.call_function(w_meth, *args)

def get_appbridge_cache(space):
    return space.fromcache(AppBridgeCache)
