from pypy.objspace.flow.model import Constant, Variable, Atom
from pypy.rpython.ootypesystem.ootype import List, Record, Instance
from pypy.rpython.ootypesystem.ootype import Signed, Unsigned, Float, Char
from pypy.rpython.ootypesystem.ootype import Bool, Void, UniChar, Class
from pypy.rpython.ootypesystem.ootype import StaticMethod, Meth, typeOf

def clrepr(item, symbol=False):
    """ This is the main repr function and is the only one that should be
    used to represent python values in lisp.
    """
    if item is None:
        return "nil"

    fun = bltn_dispatch.get(type(item), None)
    if fun is not None:
        return fun(item, symbol)

    if typeOf(item) is Class:
        return "'" + item._INSTANCE._name
    return repr_unknown(item)

def repr_const(item):
    fun = dispatch.get(type(item.concretetype), None)
    if fun is not None:
        return fun(item)

    fun = dispatch.get(item.concretetype, None)
    if fun is not None:
        return fun(item)

    if item.value is None:
        return "nil"

    return repr_unknown(item)

def repr_bltn_str(item, symbol):
    if symbol:
        return item.replace('_', '-')
    if len(item) == 1:
        return "#\\%c" % (item,)
    return '"%s"' % (item,)

def repr_bltn_bool(item, _):
    if item: 
        return "t"
    else:
        return "nil"

def repr_bltn_number(item, _):
    return str(item)

def repr_bltn_seq(item, _):
    return "'(" + ' '.join(item) + ")"

def repr_Variable(item, _):
    return clrepr(item.name, symbol=True)

def repr_Constant(item, _):
    return repr_const(item)

def repr_Instance(item, _):
    return "'" + clrepr(item._name, symbol=True)

bltn_dispatch = {
    str: repr_bltn_str,
    bool: repr_bltn_bool,
    int: repr_bltn_number,
    long: repr_bltn_number,
    float: repr_bltn_number,
    list: repr_bltn_seq,
    tuple: repr_bltn_seq,
    Variable: repr_Variable,
    Constant: repr_Constant,
    Instance: repr_Instance
}

def repr_atom(atom):
    return "'" + clrepr(str(atom), symbol=True)

def repr_class(item):
    return clrepr(item.value._INSTANCE._name, symbol=True)

def repr_void(item):
    return "nil"

def repr_bool(item):
    if item.value:
        return "t"
    else:
        return "nil"

def repr_int(item):
    return str(item.value)
    
def repr_float(item):
    return str(item.value)

def repr_list(item):
    val = map(clrepr, item.value)
    return "'(%s)" % ' '.join(val)

def repr_record(item):
    val = map(clrepr, item.value)
    return "#(%s)" % ' '.join(val)

def repr_instance(item):
    return "'" + repr_class(item)

def repr_static_method(item):
    return clrepr(item.value._name, symbol=True)

dispatch = {
        Class: repr_class,
        Void: repr_void,
        Bool: repr_bool,
        Signed: repr_int,
        Unsigned: repr_int,
        Float: repr_float,
        Atom: repr_atom,
        List: repr_list,
        Record: repr_record,
        Instance: repr_instance,
        StaticMethod: repr_static_method
}

def repr_unknown(obj):
    name = obj.__class__.__name__
    raise NotImplementedError("cannot represent %s" % (name,))
