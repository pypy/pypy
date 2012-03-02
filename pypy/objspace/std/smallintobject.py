"""
Implementation of small ints, stored as odd-valued pointers in the
translated PyPy.  To enable them, see inttype.py.
"""
from pypy.objspace.std import intobject
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.intobject import W_AbstractIntObject, W_IntObject
from pypy.interpreter.error import OperationError
from pypy.rlib.objectmodel import UnboxedValue
from pypy.rlib.rbigint import rbigint
from pypy.rlib.rarithmetic import r_uint
from pypy.tool.sourcetools import func_with_new_name
from pypy.objspace.std.inttype import wrapint

class W_SmallIntObject(W_AbstractIntObject, UnboxedValue):
    __slots__ = 'intval'
    from pypy.objspace.std.inttype import int_typedef as typedef

    def unwrap(w_self, space):
        return int(w_self.intval)
    int_w = unwrap

    def uint_w(w_self, space):
        intval = w_self.intval
        if intval < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("cannot convert negative integer to unsigned"))
        else:
            return r_uint(intval)

    def bigint_w(w_self, space):
        return rbigint.fromint(w_self.intval)


registerimplementation(W_SmallIntObject)


def delegate_SmallInt2Int(space, w_small):
    return W_IntObject(w_small.intval)

def delegate_SmallInt2Long(space, w_small):
    return space.newlong(w_small.intval)

def delegate_SmallInt2Float(space, w_small):
    return space.newfloat(float(w_small.intval))

def delegate_SmallInt2Complex(space, w_small):
    return space.newcomplex(float(w_small.intval), 0.0)

def add__SmallInt_SmallInt(space, w_a, w_b):
    return wrapint(space, w_a.intval + w_b.intval) # cannot overflow

def sub__SmallInt_SmallInt(space, w_a, w_b):
    return wrapint(space, w_a.intval - w_b.intval) # cannot overflow

def floordiv__SmallInt_SmallInt(space, w_a, w_b):
    return wrapint(space, w_a.intval // w_b.intval) # cannot overflow

div__SmallInt_SmallInt = floordiv__SmallInt_SmallInt

def mod__SmallInt_SmallInt(space, w_a, w_b):
    return wrapint(space, w_a.intval % w_b.intval) # cannot overflow

def divmod__SmallInt_SmallInt(space, w_a, w_b):
    w = wrapint(space, w_a.intval // w_b.intval) # cannot overflow
    z = wrapint(space, w_a.intval % w_b.intval)
    return space.newtuple([w, z])

def copy_multimethods(ns):
    """Copy integer multimethods for small int."""
    for name, func in intobject.__dict__.iteritems():
        if "__Int" in name:
            new_name = name.replace("Int", "SmallInt")
            if new_name not in ns:
                # Copy the function, so the annotator specializes it for
                # W_SmallIntObject.
                ns[new_name] = func = func_with_new_name(func, new_name, globals=ns)
        else:
            ns[name] = func
    ns["get_integer"] = ns["pos__SmallInt"] = ns["int__SmallInt"]
    ns["get_negint"] = ns["neg__SmallInt"]

copy_multimethods(globals())

register_all(vars())
