import py
from pypy.tool import isolate
from pypy.translator.llvm.genllvm import genllvm_compile
from pypy.translator.llvm.buildllvm import llvm_is_on_path, llvm_version
optimize_tests = False
MINIMUM_LLVM_VERSION = 1.7

ext_modules = []

def _cleanup(leave=5):
    # no test should ever need more than 5 compiled functions
    mods = ext_modules[:]
    for mod in ext_modules[:-leave]:
        if isinstance(mod, isolate.Isolate):
            isolate.close_isolate(mod)        
    del ext_modules[:-leave]
    
def teardown_module(mod):
    _cleanup(leave=0)
    
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

def compile_test(function, annotation, **kwds):
    " returns module and compiled function "
    if llvm_test():
        _cleanup()
        optimize = kwds.pop('optimize', optimize_tests)
        mod, fn = genllvm_compile(function, annotation, optimize=optimize,
                               logging=False, **kwds)
        ext_modules.append(mod)
        return mod, fn

def compile_function(function, annotation, **kwds):
    " returns compiled function "
    return compile_test(function, annotation, **kwds)[1]

