from rpython.rlib.objectmodel import specialize

class AppBridgeCache(object):
    w__mean = None
    w__var = None
    w__std = None
    w_module = None
    w_array_repr = None
    w_array_str = None

    def __init__(self, space):
        self.w_import = space.appexec([], """():
        def f():
            import sys
            __import__('numpypy.core._methods')
            return sys.modules['numpypy.core._methods']
        return f
        """)

    @specialize.arg(2)
    def call_method(self, space, name, w_obj, args):
        w_meth = getattr(self, 'w_' + name)
        if w_meth is None:
            if self.w_module is None:
                self.w_module = space.call_function(self.w_import)
            w_meth = space.getattr(self.w_module, space.wrap(name))
            setattr(self, 'w_' + name, w_meth)
        return space.call_args(w_meth, args.prepend(w_obj))

def set_string_function(space, w_f, w_repr):
    cache = get_appbridge_cache(space)
    if space.is_true(w_repr):
        cache.w_array_repr = w_f
    else:
        cache.w_array_str = w_f

def get_appbridge_cache(space):
    return space.fromcache(AppBridgeCache)
