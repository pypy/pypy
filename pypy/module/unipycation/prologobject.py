from rpython.rlib.objectmodel import specialize

from prolog.interpreter import term, error

class PythonBlackBox(term.NonVar):
    TYPE_STANDARD_ORDER = 4

    _immutable_fields_ = ["obj"]

    def __init__(self, space, val):
        self.space = space
        self.obj = val

    @specialize.arg(3)
    def basic_unify(self, other, heap, occurs_check):
        if isinstance(other, PythonBlackBox) and self.space.is_w(other.obj, self.obj):
            return
        raise error.UnificationFailed

    def copy_and_basic_unify(self, other, heap, env):
        if isinstance(other, PythonBlackBox) and self.space.is_w(other.obj, self.obj):
            return self
        else:
            raise UnificationFailed

    def __str__(self):
        return repr(self.obj)

    def __repr__(self):
        return "<PythonBlackBox %s>" % (self.obj, )

    def cmp_standard_order(self, other, heap):
        raise NotImplementedError

    def quick_unify_check(self, other):
        other = other.dereference(None)
        if isinstance(other, term.Var):
            return True
        return isinstance(other, PythonBlackBox)

