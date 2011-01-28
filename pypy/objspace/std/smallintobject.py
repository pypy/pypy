"""
Implementation of small ints, stored as odd-valued pointers in the
translated PyPy.  To enable them, see inttype.py.
"""
from pypy.objspace.std import intobject
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.intobject import W_IntObject
from pypy.rlib.objectmodel import UnboxedValue
from pypy.tool.sourcetools import func_with_new_name


class W_SmallIntObject(W_Object, UnboxedValue):
    __slots__ = 'intval'
    from pypy.objspace.std.inttype import int_typedef as typedef

    def unwrap(w_self, space):
        return int(w_self.intval)


registerimplementation(W_SmallIntObject)


def delegate_SmallInt2Int(space, w_small):
    return W_IntObject(w_small.intval)

def delegate_SmallInt2Long(space, w_small):
    return space.newlong(w_small.intval)

def delegate_SmallInt2Float(space, w_small):
    return space.newfloat(float(w_small.intval))

def delegate_SmallInt2Complex(space, w_small):
    return space.newcomplex(float(w_small.intval), 0.0)

def copy_multimethods(ns):
    """Copy integer multimethods for small int."""
    for name, func in intobject.__dict__.iteritems():
        if "__Int" in name:
            new_name = name.replace("Int", "SmallInt")
            # Copy the function, so the annotator specializes it for
            # W_SmallIntObject.
            ns[new_name] = func_with_new_name(func, new_name)
    ns["get_integer"] = ns["pos__SmallInt"] = ns["int__SmallInt"]
    ns["get_negint"] = ns["neg__SmallInt"]

copy_multimethods(globals())

register_all(vars())
