"""

Helpers to build extension modules.

"""

from pypy.interpreter import gateway
from pypy.interpreter.miscutils import InitializedClass, RwDictProxy
from pypy.interpreter.module import Module


class ExtModule(Module):
    """An empty extension module.
    Non-empty extension modules are made by subclassing ExtModule."""

    def __init__(self, space):
        Module.__init__(self, space, space.wrap(self.__name__))
        
        # to build the dictionary of the module we get all the objects
        # accessible as 'self.xxx'. Methods are bound.
        for cls in self.__class__.__mro__:
            for name in cls.__dict__:
                # ignore names in '_xyz'
                if not name.startswith('_') or name.endswith('_'):
                    value = cls.__dict__[name]
                    if isinstance(value, gateway.Gateway):
                        name = value.name
                        value = value.__get__(self)  # get a Method
                    elif hasattr(value, '__get__'):
                        continue  # ignore CPython functions

                    # ignore tricky class-attrs we can't send from interp to app-level 
                    if name in ('__metaclass__', '__init__', '__new__', ): 
                        continue  
                    space.call_method(self.w_dict, 'setdefault', 
                                      space.wrap(name), space.wrap(value))

    __metaclass__ = InitializedClass
    def __initclass__(cls):
        gateway.exportall(RwDictProxy(cls))   # xxx() -> app_xxx()
        gateway.importall(RwDictProxy(cls))   # app_xxx() -> xxx()

    def _eval_app_source(self, sourcestring):
        """ compile/execute a sourcestring in the applevel module dictionary """
        w = self.space.wrap
        w_code = self.compile(w(sourcestring), w('<pypyinline>'), w('exec'))
        code = self.space.unwrap(w_code)
        code.exec_code(self.space, self.w_dict, self.w_dict)

        # XXX do we actually want an interp-proxy to the app-level thing here? 
        #     or no interp-level "mirror" at all? 
        co = compile(sourcestring, '<inline>','exec', 4096)
        exec co in self.__dict__
