import py
from pypy.tool import isolate
from pypy.translator.llvm.genllvm import genllvm_compile
from pypy.translator.llvm.buildllvm import llvm_is_on_path, llvm_version
optimize_tests = False
MINIMUM_LLVM_VERSION = 1.7

ext_modules = []

# test options
run_isolated_only = True
do_not_isolate = False

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
        return False
    v = llvm_version()
    if v < MINIMUM_LLVM_VERSION:
        py.test.skip("llvm version not up-to-date (found "
                     "%.1f, should be >= %.1f)" % (v, MINIMUM_LLVM_VERSION))
        return False
    return True

def compile_test(function, annotation, isolate=True, **kwds):
    " returns module and compiled function "    
    if llvm_test():
        if run_isolated_only and not isolate:
            py.test.skip("skipping not isolated test")

        # turn off isolation?
        isolate = isolate and not do_not_isolate
            
        # maintain only 3 isolated process (if any)
        _cleanup(leave=3)
        optimize = kwds.pop('optimize', optimize_tests)
        mod, fn = genllvm_compile(function, annotation, optimize=optimize,
                                  logging=False, isolate=isolate, **kwds)
        if isolate:
            ext_modules.append(mod)
        return mod, fn

def compile_function(function, annotation, isolate=True, **kwds):
    " returns compiled function "
    return compile_test(function, annotation, isolate=isolate, **kwds)[1]

