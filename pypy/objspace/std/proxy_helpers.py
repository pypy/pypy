
""" Some transparent helpers, put here because
of cyclic imports
"""

from pypy.objspace.std.model import W_ANY, W_Object
from pypy.interpreter import baseobjspace
from pypy.interpreter.argument import Arguments
from pypy.tool.sourcetools import func_with_new_name

def create_mm_names(classname, mm, is_local):
    s = ""
    if is_local:
        s += "list_"
    s += mm.name + "__"
    s += "_".join([classname] + ["ANY"] * (mm.arity - 1))
    #if '__' + mm.name + '__' in mm.specialnames:
    #    return s, '__' + mm.name + '__'
    if mm.specialnames:
        return s, mm.specialnames[0]
    return s, mm.name

def install_general_args_trampoline(type_, mm, is_local, op_name):
    def function(space, w_transparent_list, __args__):
        args = __args__.prepend(space.wrap(op_name))
        return space.call_args(w_transparent_list.w_controller, args)
    
    function = func_with_new_name(function, mm.name)
    mm.register(function, type_)

def install_w_args_trampoline(type_, mm, is_local, op_name):
    def function(space, w_transparent_list, *args_w):
        args = Arguments(space, [space.wrap(op_name)] + list(args_w[:-1]), w_stararg=args_w[-1])
        return space.call_args(w_transparent_list.w_controller, args)
    
    function = func_with_new_name(function, mm.name)
    mm.register(function, type_, *([W_ANY] * (mm.arity - 1)))

def install_mm_trampoline(type_, mm, is_local):
    classname = type_.__name__[2:]
    mm_name, op_name = create_mm_names(classname, mm, is_local)
    
    if ['__args__'] == mm.argnames_after:
        return install_general_args_trampoline(type_, mm, is_local, op_name)
    if ['w_args'] == mm.argnames_after:
        return install_w_args_trampoline(type_, mm, is_local, op_name)
    assert not mm.argnames_after
    # we search here for special-cased stuff
    def function(space, w_transparent_list, *args_w):
        return space.call_function(w_transparent_list.w_controller, space.wrap\
            (op_name), *args_w)
    function = func_with_new_name(function, mm_name)
    mm.register(function, type_, *([W_ANY] * (mm.arity - 1)))

def is_special_doublearg(mm, type_):
    """ We specialcase when we've got two argument method for which
    there exist reverse operation
    """
    if mm.arity != 2:
        return False
    
    if len(mm.specialnames) != 2:
        return False
    
    # search over the signatures
    for signature in mm.signatures():
        if signature == (type_.original, type_.original):
            return True
    return False

def install_mm_special(type_, mm, is_local):
    classname = type_.__name__[2:]
    #mm_name, op_name = create_mm_names(classname, mm, is_local)
    
    def function(space, w_any, w_transparent_list):
        retval = space.call_function(w_transparent_list.w_controller, space.wrap(mm.specialnames[1]),
            w_any)
        return retval
        
    function = func_with_new_name(function, mm.specialnames[0])
    
    mm.register(function, type_.typedef.any, type_)

def register_type(type_):
    from pypy.objspace.std.stdtypedef import multimethods_defined_on
    
    for mm, is_local in multimethods_defined_on(type_.original):
        if not mm.name.startswith('__'):
            install_mm_trampoline(type_, mm, is_local)
            if is_special_doublearg(mm, type_):
                install_mm_special(type_, mm, is_local)
