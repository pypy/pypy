from pypy.objspace.flow.model import Constant, Variable, last_exception
from pypy.rpython.ootypesystem.ootype import _static_meth, Instance

def repr_unknown(obj):
    return '#<%r>' % (obj,)

def repr_var(var):
    return var.name
    
def repr_class_name(name):
    return name.replace('_', '-')

def repr_fun_name(name):
    return name.replace('_', '-')

def repr_const(val):
    if isinstance(val, _static_meth):
        return repr_fun_name(val._name) # XXX make sure function names are unique
    if isinstance(val, tuple):
        val = map(repr_const, val)
        return "'(%s)" % ' '.join(val)
    elif isinstance(val, bool): # should precedes int
        if val:
            return "t"
        else:
            return "nil"
    elif isinstance(val, (int, long)):
        return str(val)
    elif val is None:
        return "nil"
    elif isinstance(val, str):
        val.replace("\\", "\\\\")
        val.replace("\"", "\\\"")
        val = '"' + val + '"'
        return val
    else:
        return repr_unknown(val)

def repr_arg(arg):
    if isinstance(arg, Variable):
        return repr_var(arg)
    elif isinstance(arg, Constant):
        return repr_const(arg.value)
    else:
        return repr_unknown(arg)
