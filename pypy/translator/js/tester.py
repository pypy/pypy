
""" tester - support module for testing js code inside python

Needs to be imported in case one wants tests involving calling BasicExternal
methods
"""

from pypy.rpython.ootypesystem.bltregistry import BasicExternal

def __getattr__(self, attr):
    val = super(BasicExternal, self).__getattribute__(attr)
    if not callable(val) or attr not in self._methods:
        return val # we don't do anything special
    # otherwise....
    def wrapper(*args, **kwargs):
        args = list(args)
        # do this only if last arg is callable
        if not (len(args) > 0 and callable(args[-1])):
            return val(*args, **kwargs)
        callback = args.pop()
        res = val(*args, **kwargs)
        if not hasattr(self, '__callbacks'):
            self.__callbacks = []
        self.__callbacks.append((callback, res))
    wrapper.func_name = attr
    return wrapper

BasicExternal.__getattribute__ = __getattr__

def schedule_callbacks(*args):
    for arg in args:
        if hasattr(arg, '__callbacks'):
            for callback, res in arg.__callbacks:
                callback(res)
