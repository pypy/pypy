
""" Various simple support functions
"""

from pypy.rpython.ootypesystem.bltregistry import described, load_dict_args,\
     MethodDesc

from pypy.rpython.extfunc import _callable

def callback(retval=None, args={}):
    """ Variant of described decorator, which flows
    an additional argument with return value of decorated
    function, used specifically for callbacks
    """
    def decorator(func):
        defs = func.func_defaults
        if defs is None:
            defs = ()
        vars = func.func_code.co_varnames[:func.func_code.co_argcount]
        arg_list = load_dict_args(vars, defs, args)
        arg_list.append(("callback", _callable(args=[retval])))
        func._method = (func.__name__, MethodDesc(arg_list, retval))
        return func

    return decorator
