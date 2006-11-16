
import sys, new
from pypy.translator.js.main import rpython2javascript

def js_source(functions):
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
        return rpython2javascript(mod, function_names)
    finally:
        del sys.modules['_js_src']

