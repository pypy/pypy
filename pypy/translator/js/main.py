"""Contains high level javascript compilation function
"""

import autopath

#from pypy.translator.js.test.runtest import compile_function
#from pypy.translator.translator import TranslationContext
from pypy.translator.driver import TranslationDriver
from pypy.translator.js.js import JS
from pypy.tool.error import AnnotatorError, FlowingError, debug
from pypy.rpython.nonconst import NonConstant
from pypy.annotation.policy import AnnotatorPolicy

class FunctionNotFound(Exception):
    pass

class BadSignature(Exception):
    pass

class JsPolicy(AnnotatorPolicy):
    allow_someobjects = False

def get_args(func_data):
    l = []
    for i in xrange(func_data.func_code.co_argcount):
        l.append("NonConstant(%s)" % repr(func_data.func_defaults[i]))
    return "(%s)" % ",".join(l)

def rpython2javascript_main(argv):
    if len(argv) < 1:
        print "usage: module <function_names>"
        import sys
        sys.exit(0)
    module_name = argv[0]
    if module_name.endswith('.py'):
        module_name = module_name[:-3]
    function_names = argv[1:]
    mod = __import__(module_name, None, None, ["Module"])
    return rpython2javascript(mod, function_names)

def rpython2javascript(mod, function_names):
    module_name = mod.__name__
    if not function_names and 'main' in mod.__dict__:
        function_names.append('main')
    for func_name in function_names:
        if func_name not in mod.__dict__:
            raise FunctionNotFound("function %r was not found in module %r" % (func_name, module_name))
        func_code = mod.__dict__[func_name]
        if func_code.func_code.co_argcount > 0 and func_code.func_code.co_argcount != len(func_code.func_defaults):
            raise BadSignature("Function %s does not have default arguments" % func_name)
    source_ssf = "\n".join(["import %s" % module_name, "def some_strange_function_which_will_never_be_called():"] + ["  "+\
        module_name+"."+fun_name+get_args(mod.__dict__[fun_name]) for fun_name in function_names])
    print source_ssf
    exec(source_ssf) in globals()
    #fn = compile_function([mod.__dict__[f_name] for f_name in function_names], [[] for i in function_names])
    # now we gonna just cut off not needed function
    driver = TranslationDriver()
    try:
        driver.setup(some_strange_function_which_will_never_be_called, [], policy = JsPolicy())
        driver.proceed(["compile_js"])
        return driver.gen.tmpfile.open().read()
    except Exception, e:
        # do something nice with it
        debug(driver)
