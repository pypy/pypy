import py
from pypy.tool import isolate
from pypy.translator.llvm.buildllvm import llvm_is_on_path, llvm_version, gcc_version
from pypy.translator.llvm.genllvm import GenLLVM

optimize_tests = False
MINIMUM_LLVM_VERSION = 1.9

ext_modules = []

# test options
run_isolated_only = True
do_not_isolate = False

from pypy import conftest

def _cleanup(leave=0):
    # no test should ever need more than 5 compiled functions
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

def gcc3_test():
    gcc_ver = gcc_version()
    if int(gcc_ver) != 3:
        py.test.skip("test required gcc version 3 (found version %.1f)" % gcc_ver)
        return False
    return True

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

def compile_test(function, annotation, isolate=True, **kwds):
    " returns module and compiled function "    
    llvm_test()
    if run_isolated_only and not isolate:
        py.test.skip("skipping not isolated test")

    # turn off isolation?
    isolate = isolate and not do_not_isolate

    # maintain only 3 isolated process (if any)
    _cleanup(leave=3)
    optimize = kwds.pop('optimize', optimize_tests)
    mod, fn = genllvm_compile(function, annotation, optimize=optimize,
                              isolate=isolate, **kwds)
    if isolate:
        ext_modules.append(mod)
    return mod, fn

def compile_function(function, annotation, isolate=True, **kwds):
    " returns compiled function "
    return compile_test(function, annotation, isolate=isolate, **kwds)[1]

