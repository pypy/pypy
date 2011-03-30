# NOT_RPYTHON

# For now this is here, living at app-level.
#
# The issue is that for now we don't support writing interp-level
# subclasses of Wrappable that inherit at app-level from a type like
# 'dict'.  But what we can do is write individual methods at
# interp-level.

import _collections


class defaultdict(dict):
    
    def __init__(self, *args, **kwds):
        self.default_factory = None
        if 'default_factory' in kwds:
            self.default_factory = kwds.pop('default_factory')
        elif len(args) > 0 and (callable(args[0]) or args[0] is None):
            self.default_factory = args[0]
            args = args[1:]
        super(defaultdict, self).__init__(*args, **kwds)
 
    def __missing__(self, key):
        pass    # this method is written at interp-level
    __missing__.func_code = _collections.__missing__.func_code

    def __repr__(self, recurse=set()):
        # XXX not thread-safe, but good enough
        if id(self) in recurse:
            return "defaultdict(...)"
        try:
            recurse.add(id(self))
            return "defaultdict(%s, %s)" % (repr(self.default_factory), super(defaultdict, self).__repr__())
        finally:
            recurse.remove(id(self))

    def copy(self):
        return type(self)(self, default_factory=self.default_factory)
    
    def __copy__(self):
        return self.copy()

    def __reduce__(self):
        """
        __reduce__ must return a 5-tuple as follows:

           - factory function
           - tuple of args for the factory function
           - additional state (here None)
           - sequence iterator (here None)
           - dictionary iterator (yielding successive (key, value) pairs

           This API is used by pickle.py and copy.py.
        """
        return (type(self), (self.default_factory,), None, None, self.iteritems())
