from pypy.objspace.flow.model import Constant, Variable, Atom
from pypy.rpython.rmodel import HalfConcreteWrapper
from pypy.rpython.ootypesystem.ootype import List, Record, Instance
from pypy.rpython.ootypesystem.ootype import Signed, Unsigned, Float, Char
from pypy.rpython.ootypesystem.ootype import Bool, Void, UniChar, Class
from pypy.rpython.ootypesystem.ootype import StaticMethod, Meth, typeOf
from pypy.rpython.ootypesystem.rclass import CLASSTYPE

def clrepr(item):
    if isinstance(item, str):
        if len(item) == 1:
            return "#\\" + item
        return repr_fun_name(item)
    if isinstance(item, bool):
        if item: 
            return "t"
        else:
            return "nil"
    if isinstance(item, (int, long, float)):
        return str(item)
    if isinstance(item, (list, tuple)):
        return "'(" + ' '.join(item) + ")"
    if isinstance(item, Variable):
        return repr_var(item)
    if isinstance(item, Constant):
        return repr_const(item)
    if isinstance(item, Instance):
        return "'" + repr_class_name(item._name)
    if typeOf(item) is Class:
        return "'" + item._INSTANCE._name
    return repr_unknown(item)

def repr_unknown(obj):
    name = obj.__class__.__name__
    raise NotImplementedError("cannot represent %s" % (name,))

def repr_var(var):
    return var.name

def repr_atom(atom):
    return "'" + str(atom)

def repr_class_name(name):
    return name.replace('_', '-')

def repr_fun_name(name):
    return name.replace('_', '-')

def repr_const(item):
    if isinstance(item.value, HalfConcreteWrapper):
        item = item.concretize()

    if isinstance(item.concretetype, Atom):
        return repr_atom(val)

    if isinstance(item.concretetype, List):
        val = map(repr_const, item.value)
        return "#(%s)" % ' '.join(val)

    if isinstance(item.concretetype, Record):
        val = map(repr_const, item.value)
        return "'(%s)" % ' '.join(val)

    if isinstance(item.concretetype, Instance):
        return "'" + repr_class_name(item.value._name)

    if item.concretetype is Class:
        return "'" + repr_class_name(item.value._INSTANCE._name)

    if item.concretetype is Void:
        return "nil"

    if isinstance(item.concretetype, StaticMethod):
        return repr_fun_name(item.value._name)

    if item.concretetype is Bool: # should precede int
        if item.value:
            return "t"
        else:
            return "nil"

    if item.concretetype is Signed or item.concretetype is Unsigned:
        #, long)): Not yet real longs
        return str(item.value)

    if item.concretetype is Float:
        return str(item.value)

    if item.value is None:
        return "nil"

    return repr_unknown(item)
