"""
Definition of the standard Python types.
"""

class object:
    
    def __new__(cls):
        if cls is object:
            return sys.pypy.ObjectFactory()
        else:
            return sys.pypy.UserObjectFactory(cls, sys.pypy.ObjectFactory)

    def __repr__(self):
        return '<%s object at 0x%x>' % (
            type(self).__name__, id(self))


sys.pypy.registertype(sys.pypy.ObjectFactory, object)



class int(object):

    def __new__(cls, *args):
        if cls is int:
            return sys.pypy.IntObjectFactory(args)
        else:
            return sys.pypy.UserObjectFactory(cls,
                                              sys.pypy.IntObjectFactory,
                                              args)

    def __repr__(self):
        return str(self)


sys.pypy.registertype(sys.pypy.IntObjectFactory, int)


class type(object):
    pass # ...


class dict(object):

    def __new__(cls, args):
        hello

    def get(self, k, v=None):
        if self.has_key(k):
            return self[k]
        return v


class str(object):

    def __new__(xxx):
        xxx


class function(object):

    func_code    = sys.pypy.builtin_property('fix')
    func_globals = sys.pypy.builtin_property('me')

sys.pypy.registertype(sys.pypy.FunctionFactory, function)
