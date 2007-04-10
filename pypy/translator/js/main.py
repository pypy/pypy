"""Contains high level javascript compilation function
"""

import autopath

#from pypy.translator.js.test.runtest import compile_function
#from pypy.translator.translator import TranslationContext
from pypy.translator.driver import TranslationDriver
from pypy.translator.js.js import JS
from pypy.tool.error import AnnotatorError, FlowingError, debug
from pypy.rlib.nonconst import NonConstant
from pypy.annotation.policy import AnnotatorPolicy
from py.compat import optparse
from pypy.config.config import OptionDescription, BoolOption, StrOption
from pypy.config.config import Config, to_optparse
import py
import sys

js_optiondescr = OptionDescription("jscompile", "", [
    BoolOption("view", "View flow graphs",
               default=False, cmdline="--view"),
    BoolOption("use_pdb", "Use debugger",
               default=False, cmdline="--pdb"),
    StrOption("output", "File to save results (default output.js)",
              default="output.js", cmdline="--output")])


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

def rpython2javascript_main(argv, jsconfig):
    if len(argv) == 0:
        print "usage: module <function_names>"
        sys.exit(0)
    module_name = argv[0]
    if not module_name.endswith('.py'):
        module_name += ".py"
    mod = py.path.local(module_name).pyimport()
    if len(argv) == 1:
        function_names = []
        for function_name in dir(mod):
            function = getattr(mod, function_name)
            if callable(function) and getattr(function, '_client', False):
                function_names.append( function_name )
        if not function_names:
            print "Cannot find any function with _client=True in %s"\
                      % module_name
            sys.exit(1)
    else:
        function_names = argv[1:]
    source = rpython2javascript(mod, function_names, jsconfig=jsconfig)
    if not source:
        print "Exiting, source not generated"
        sys.exit(1)
    open(jsconfig.output, "w").write(source)
    print "Written file %s" % jsconfig.output

# some strange function source
source_ssf_base = """

import %(module_name)s
from pypy.translator.js.helper import __show_traceback
from pypy.rlib.nonconst import NonConstant as NonConst

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

def get_source_ssf(mod, module_name, function_names):
    #source_ssf = "\n".join(["import %s" % module_name, "def some_strange_function_which_will_never_be_called():"] + ["  "+\
    #    module_name+"."+fun_name+get_args(mod.__dict__[fun_name]) for fun_name in function_names])
    function_list = []
    function_def_list = []
    for fun_name in function_names:
        args = get_args(mod.__dict__[fun_name])
        arg_names = get_arg_names(mod.__dict__[fun_name])
        base = function_base
        function_list.append(py.code.Source(base % locals()))
    function_defs = "\n\n".join([str(i) for i in function_def_list])
    functions = "\n".join([str(i.indent()) for i in function_list])
    retval = source_ssf_base % locals()
    print retval
    return retval

def rpython2javascript(mod, function_names, jsconfig=None, use_pdb=True):
    if isinstance(function_names, str):
        function_names = [function_names]
        # avoid confusion
    if mod is None:
        # this means actual module, which is quite hairy to get in python,
        # so we cheat
        import sys
        mod = sys.modules[sys._getframe(1).f_globals['__name__']]
    
    if jsconfig is None:
        jsconfig = Config(js_optiondescr)
    if use_pdb:
        jsconfig.use_pdb = True
    module_name = mod.__name__
    if not function_names and 'main' in mod.__dict__:
        function_names.append('main')
    for func_name in function_names:
        if func_name not in mod.__dict__:
            raise FunctionNotFound("function %r was not found in module %r" % (func_name, module_name))
        func_code = mod.__dict__[func_name]
        if func_code.func_defaults:
            lgt = len(func_code.func_defaults)
        else:
            lgt = 0
        if func_code.func_code.co_argcount > 0 and func_code.func_code. \
                co_argcount != lgt:
            raise BadSignature("Function %s does not have default arguments" % func_name)
    source_ssf = get_source_ssf(mod, module_name, function_names)
    exec(source_ssf) in globals()
    # now we gonna just cut off not needed function
    # XXX: Really do that
    #options = optparse.Values(defaults=DEFAULT_OPTIONS)
    from pypy.config.pypyoption import get_pypy_config
    config = get_pypy_config(translating=True)
    driver = TranslationDriver(config=config)
    try:
        driver.setup(some_strange_function_which_will_never_be_called, [], policy = JsPolicy())
        driver.proceed(["compile_js"])
        if jsconfig.view:
            driver.translator.view()
        return driver.gen.tmpfile.open().read()
        # XXX: Add some possibility to write down selected file
    except Exception, e:
        # do something nice with it
        debug(driver, use_pdb)
