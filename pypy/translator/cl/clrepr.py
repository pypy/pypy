import types

from pypy.objspace.flow.model import Constant, Variable
from pypy.rpython.ootypesystem.ootype import List, Record, Instance, instance_impl, _static_meth
from pypy.rpython.ootypesystem.rclass import CLASSTYPE

def repr_unknown(obj):
    name = obj.__class__.__name__
    raise NotImplementedError("cannot represent %s" % (name,))

def repr_var(var):
    return var.name
    
def repr_class_name(name):
    return name.replace('_', '-')

def repr_fun_name(name):
    return name.replace('_', '-')

def repr_const(val):
    if isinstance(val, List):
        return "'array"
    if isinstance(val, Record):
        return "'struct" # XXX
    if isinstance(val, Instance):
        return "'" + repr_class_name(val._name)
    if isinstance(val, instance_impl):
        if val._TYPE is CLASSTYPE:
            return "'standard-class"
    if isinstance(val, types.FunctionType):
        if val.func_name == 'dum_nocheck': # XXX
            return "'dummy"
    if isinstance(val, _static_meth):
        return repr_fun_name(val._name) # XXX make sure function names are unique
    if isinstance(val, tuple):
        val = map(repr_const, val)
        return "'(%s)" % ' '.join(val)
    if isinstance(val, list):
        val = map(repr_const, val)
        return "#(%s)" % ' '.join(val)
    if isinstance(val, bool): # should precede int
        if val:
            return "t"
        else:
            return "nil"
    if isinstance(val, (int, long)):
        return str(val)
    if val is None:
        return "nil"
    if isinstance(val, str):
        if len(val) == 1:
            return "#\%c" % (val,)
        else:
            val.replace("\\", "\\\\")
            val.replace("\"", "\\\"")
            val = '"' + val + '"'
            return val
    return repr_unknown(val)

def repr_arg(arg):
    if isinstance(arg, Variable):
        return repr_var(arg)
    if isinstance(arg, Constant):
        return repr_const(arg.value)
    return repr_unknown(arg)
