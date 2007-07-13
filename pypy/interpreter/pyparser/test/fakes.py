
class FakeSpace:
    w_None = None
    w_str = str
    w_basestring = basestring
    w_int = int

    def wrap(self, obj):
        return obj

    def unwrap(self, obj):
        return obj

    def isinstance(self, obj, wtype ):
        return isinstance(obj,wtype)

    def is_true(self, obj):
        return obj

    def eq_w(self, obj1, obj2):
        return obj1 == obj2

    def is_w(self, obj1, obj2):
        return obj1 is obj2

    def type(self, obj):
        return type(obj)

    def newlist(self, lst):
        return list(lst)

    def newtuple(self, lst):
        return tuple(lst)

    def call_method(self, obj, meth, *args):
        return getattr(obj, meth)(*args)

    def call_function(self, func, *args):
        return func(*args)

    builtin = dict(int=int, long=long, float=float, complex=complex)
