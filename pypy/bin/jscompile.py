#!/usr/bin/env python
""" RPython to javascript compiler
Usage: jscompiler module_to_compile [list of functions to export]
"""

import autopath
import sys

from pypy.translator.js.test.runtest import compile_function
from pypy.translator.translator import TranslationContext
from pypy.translator.js.js import JS
from pypy.tool.error import AnnotatorError, FlowingError

class FunctionNotFound(Exception):
    pass

class BadSignature(Exception):
    pass

def get_args(func_data):
    l = []
    for i in xrange(func_data.func_code.co_argcount):
        l.append(repr(func_data.func_defaults[i]))
    return "(%s)" % ",".join(l)

def _main(argv):
    if len(argv) < 3:
        print __doc__
        sys.exit(0)
    module_name = argv[1]
    function_names = argv[2:]
    mod = __import__(module_name, None, None, ["Module"])
    for func_name in function_names:
        if func_name not in mod.__dict__:
            raise FunctionNotFound("function %r was not found in module %r" % (func_name, module_name))
        func_code = mod.__dict__[func_name]
        if func_code.func_code.co_argcount > 0 and func_code.func_code.co_argcount != len(func_code.func_defaults):
            raise BadSignature("Function %s does not have default arguments" % func_name)
    source_ssf = "\n".join(["import %s" % module_name, "def some_strange_function_which_will_never_be_called():"] + ["  "+\
        module_name+"."+fun_name+get_args(mod.__dict__[func_name]) for fun_name in function_names])
    print source_ssf
    exec(source_ssf) in globals()
    #fn = compile_function([mod.__dict__[f_name] for f_name in function_names], [[] for i in function_names])
    # now we gonna just cut off not needed function
    try:
        t = TranslationContext()
        t.buildannotator().build_types(some_strange_function_which_will_never_be_called, [])
        t.buildrtyper(type_system="ootype").specialize() 
        j = JS(t, [mod.__dict__[f_name] for f_name in function_names], False)
        j.write_source()
        f = open("out.js", "w")
        f.write(j.tmpfile.open().read())
        f.close()
    except (AnnotatorError, FlowingError), e:
        # do something nice with it
        raise
    
if __name__ == '__main__':
    _main(sys.argv)
