from __future__ import nested_scopes
import operator
from pypy.interpreter.baseobjspace import *


class W_Object:
    pass

class W_Anything(W_Object):
    pass

class W_Constant(W_Object):
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return '<constant %r>' % self.value


class AnnException(Exception):
    pass


class AnnotationObjSpace(ObjSpace):

    def initialize(self):
        self.w_None = self.wrap(None)
        self.w_True = self.wrap(True)
        self.w_False = self.wrap(False)
        self.w_NotImplemented = self.wrap(NotImplemented)
        self.w_Ellipsis = self.wrap(Ellipsis)
        import __builtin__, types
        for n, c in __builtin__.__dict__.iteritems():
            if isinstance(c, (types.TypeType, Exception)):
                setattr(self, 'w_' + c.__name__, self.wrap(c))
        self.w_builtins = self.wrap(__builtin__)

    def wrap(self, obj):
        return W_Constant(obj)

    def unwrap(self, w_obj):
        if isinstance(w_obj, W_Constant):
            return w_obj.value
        else:
            raise AnnException, "Cannot unwrap %r" % w_obj
    
    def newtuple(self, args_w):
        return W_Anything()

    def newdict(self, items_w):
        for w_key, w_value in items_w:
            if (not isinstance(w_key, W_Constant) or
                not isinstance(w_value, W_Constant)):
                break
        else:
            d = {}
            for w_key, w_value in items_w:
                d[self.unwrap(w_key)] = self.unwrap(w_value)
            return self.wrap(d)

        return W_Anything()

    def newmodule(self, w_name):
        return W_Anything()

    def newfunction(self, *stuff):
        return W_Anything()



def make_op(name, symbol, arity, specialnames):
    
    def generic_operator(space, *args_w):
        assert len(args_w) == arity, "got a wrong number of arguments"
        for w_arg in args_w:
            if not isinstance(w_arg, W_Constant):
                break
        else:
            # all arguments are constants, call the operator now
            op = getattr(operator, name)
            return op(*[space.unwrap(w_arg) for w_arg in args_w])

        return W_Anything()
    
    setattr(AnnotationObjSpace, name, generic_operator)

for line in ObjSpace.MethodTable:
    make_op(*line)
