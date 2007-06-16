
""" Various simple support functions
"""

from pypy.rpython.ootypesystem.bltregistry import described, load_dict_args,\
     MethodDesc

from pypy.rpython.extfunc import genericcallable

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
        if isinstance(args, dict):
            arg_list = load_dict_args(vars, defs, args)
        else:
            arg_list = args
        arg_list.append(("callback", genericcallable(args=[retval])))
        func._method = (func.__name__, MethodDesc(arg_list, retval))
        return func

    return decorator

import sys, new
from pypy.translator.js.main import rpython2javascript

def js_source(functions, use_pdb=True):
    mod = new.module('_js_src')
    function_names = []
    for func in functions:
        name = func.__name__
        if hasattr(mod, name):
            raise ValueError("exported function name %r is duplicated"
                             % (name,))
        mod.__dict__[name] = func
        function_names.append(name)
    sys.modules['_js_src'] = mod
    try:
        return rpython2javascript(mod, function_names, use_pdb=use_pdb)
    finally:
        del sys.modules['_js_src']

