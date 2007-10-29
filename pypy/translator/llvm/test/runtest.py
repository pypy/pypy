import py
py.test.skip("llvm is a state of flux")

from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin
from pypy.translator.llvm.buildllvm import llvm_is_on_path, llvm_version, gcc_version
from pypy.translator.llvm.genllvm import GenLLVM

optimize_tests = False
MINIMUM_LLVM_VERSION = 1.9

ext_modules = []

# prevents resource leaking
use_isolate = True

# if test can't be run using isolate, skip the test (useful for buildbots)
run_isolated_only = True

from pypy import conftest

def _cleanup(leave=0):
    from pypy.tool import isolate
    if leave:
        mods = ext_modules[:-leave]
    else:        
        mods = ext_modules
    for mod in mods:
        if isinstance(mod, isolate.Isolate):
            isolate.close_isolate(mod)        
    if leave:
        del ext_modules[:-leave]
    else:
        del ext_modules[:]
            
def teardown_module(mod):
    _cleanup()
    
def llvm_test():
    if not llvm_is_on_path():
        py.test.skip("could not find one of llvm-as or llvm-gcc")
    llvm_ver = llvm_version()
    if llvm_ver < MINIMUM_LLVM_VERSION:
        py.test.skip("llvm version not up-to-date (found "
                     "%.1f, should be >= %.1f)" % (llvm_ver, MINIMUM_LLVM_VERSION))

#______________________________________________________________________________

def genllvm_compile(function,
                    annotation,
                    
                    # debug options
                    debug=True,
                    logging=False,
                    isolate=True,

                    # pass to compile
                    optimize=True,
                    extra_opts={}):

    """ helper for genllvm """

    from pypy.translator.driver import TranslationDriver
    from pypy.config.pypyoption import get_pypy_config
    config = get_pypy_config({}, translating=True)
    options = {
        'translation.backend': 'llvm',
        'translation.llvm.debug': debug,
        'translation.llvm.logging': logging,
        'translation.llvm.isolate': isolate,
        'translation.backendopt.none': not optimize,
        'translation.gc': 'boehm',
        }
    options.update(extra_opts)
    config.set(**options)
    driver = TranslationDriver(config=config)
    driver.setup(function, annotation)
    driver.annotate()
    if conftest.option.view:
        driver.translator.view()
    driver.rtype()
    if conftest.option.view:
        driver.translator.view()
    driver.compile() 
    if conftest.option.view:
        driver.translator.view()
    return driver.c_module, driver.c_entryp

def compile_test(function, annotation, isolate_hint=True, **kwds):
    " returns module and compiled function "    
    llvm_test()

    if run_isolated_only and not isolate_hint:
        py.test.skip("skipping unrecommended isolated test")

    # turn off isolation?
    isolate = use_isolate and isolate_hint

    # maintain only 3 isolated process (if any)
    _cleanup(leave=3)
    optimize = kwds.pop('optimize', optimize_tests)
    mod, fn = genllvm_compile(function, annotation, optimize=optimize,
                              isolate=isolate, **kwds)
    if isolate:
        ext_modules.append(mod)
    return mod, fn

def compile_function(function, annotation, isolate_hint=True, **kwds):
    " returns compiled function "
    return compile_test(function, annotation, isolate_hint=isolate_hint, **kwds)[1]

# XXX Work in progress, this was mostly copied from JsTest
class LLVMTest(BaseRtypingTest, LLRtypeMixin):
    def _compile(self, _fn, args, policy=None):
        argnames = _fn.func_code.co_varnames[:_fn.func_code.co_argcount]
        func_name = _fn.func_name
        if func_name == '<lambda>':
            func_name = 'func'
        source = py.code.Source("""
        def %s():
            from pypy.rlib.nonconst import NonConstant
            res = _fn(%s)
            if isinstance(res, type(None)):
                return None
            else:
                return str(res)"""
        % (func_name, ",".join(["%s=NonConstant(%r)" % (name, i) for
                                   name, i in zip(argnames, args)])))
        exec source.compile() in locals()
        return compile_function(locals()[func_name], [])

    def interpret(self, fn, args, policy=None):
        f = self._compile(fn, args)
        res = f(*args)
        return res

    def interpret_raises(self, exception, fn, args):
        #import exceptions # needed by eval
        #try:
        #import pdb; pdb.set_trace()
        try:
            res = self.interpret(fn, args)
        except Exception, e:
            assert issubclass(eval(ex.class_name), exception)
        else:
            raise AssertionError("Did not raise, returned %s" % res)
        #except ExceptionWrapper, ex:
        #    assert issubclass(eval(ex.class_name), exception)
        #else:
        #    assert False, 'function did raise no exception at all'

