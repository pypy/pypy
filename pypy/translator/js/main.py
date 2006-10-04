"""Contains high level javascript compilation function
"""

import autopath

#from pypy.translator.js.test.runtest import compile_function
#from pypy.translator.translator import TranslationContext
from pypy.translator.driver import TranslationDriver, DEFAULT_OPTIONS
from pypy.translator.js.js import JS
from pypy.tool.error import AnnotatorError, FlowingError, debug
from pypy.rpython.nonconst import NonConstant
from pypy.annotation.policy import AnnotatorPolicy
from py.compat import optparse
import py
from pypy.tool import option

class Options(option.Options):
    view = False
    output = 'output.js'
    debug_transform = False

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
    return ",".join(l)

def get_arg_names(func_data):
    return ",".join(func_data.func_code.co_varnames\
        [:func_data.func_code.co_argcount])

def rpython2javascript_main(argv, opts):
    if len(argv) < 1:
        print "usage: module <function_names>"
        import sys
        sys.exit(0)
    module_name = argv[0]
    if module_name.endswith('.py'):
        module_name = module_name[:-3]
    function_names = argv[1:]
    mod = __import__(module_name, None, None, ["Module"])
    source = rpython2javascript(mod, function_names, opts=opts)
    if opts.output != '':
        open(opts.output, "w").write(source)
        print "Written file %s" % opts.output

# some strange function source
source_ssf_base = """

import %(module_name)s
from pypy.translator.js.helper import __show_traceback
from pypy.translator.transformer.debug import traceback_handler
from pypy.rpython.nonconst import NonConstant as NonConst

%(function_defs)s

def some_strange_function_which_will_never_be_called():
    
%(functions)s
"""

wrapped_function_def_base = """
def %(fun_name)s(%(arg_names)s):
    try:
        traceback_handler.enter(NonConst("entrypoint"), NonConst("()"), NonConst(""), NonConst(0))
        %(module_name)s.%(fun_name)s(%(arg_names)s)
        traceback_handler.leave(NonConst("entrypoint"))
    except Exception, e:
        new_tb = traceback_handler.tb[:]
        __show_traceback(new_tb, str(e))

%(fun_name)s.explicit_traceback = True
"""

function_base = "%(module_name)s.%(fun_name)s(%(args)s)"
wrapped_function_base = "%(fun_name)s(%(args)s)"

def get_source_ssf(mod, module_name, function_names, use_debug=True):
    #source_ssf = "\n".join(["import %s" % module_name, "def some_strange_function_which_will_never_be_called():"] + ["  "+\
    #    module_name+"."+fun_name+get_args(mod.__dict__[fun_name]) for fun_name in function_names])
    function_list = []
    function_def_list = []
    for fun_name in function_names:
        args = get_args(mod.__dict__[fun_name])
        arg_names = get_arg_names(mod.__dict__[fun_name])
        if not use_debug:
            base = function_base
        else:
            base = wrapped_function_base
            function_def_list.append(py.code.Source(wrapped_function_def_base %
                locals()))
        function_list.append(py.code.Source(base % locals()))
    function_defs = "\n\n".join([str(i) for i in function_def_list])
    functions = "\n".join([str(i.indent()) for i in function_list])
    retval = source_ssf_base % locals()
    print retval
    return retval

def rpython2javascript(mod, function_names, opts=Options):
    module_name = mod.__name__
    if not function_names and 'main' in mod.__dict__:
        function_names.append('main')
    for func_name in function_names:
        if func_name not in mod.__dict__:
            raise FunctionNotFound("function %r was not found in module %r" % (func_name, module_name))
        func_code = mod.__dict__[func_name]
        if func_code.func_code.co_argcount > 0 and func_code.func_code. \
                co_argcount != len(func_code.func_defaults):
            raise BadSignature("Function %s does not have default arguments" % func_name)
    source_ssf = get_source_ssf(mod, module_name, function_names, opts.debug_transform)
    exec(source_ssf) in globals()
    # now we gonna just cut off not needed function
    # XXX: Really do that
    options = optparse.Values(defaults=DEFAULT_OPTIONS)
    options.debug_transform = opts.debug_transform
    # XXX: This makes no sense (copying options)
    driver = TranslationDriver(options=options)
    try:
        driver.setup(some_strange_function_which_will_never_be_called, [], policy = JsPolicy())
        driver.proceed(["compile_js"])
        if opts.view:
            driver.translator.view()
        return driver.gen.tmpfile.open().read()
        # XXX: Add some possibility to write down selected file
    except Exception, e:
        # do something nice with it
        debug(driver)
