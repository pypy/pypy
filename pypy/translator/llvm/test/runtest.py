import py
from pypy.translator.llvm.genllvm import genllvm_compile
from pypy.translator.llvm.buildllvm import llvm_is_on_path, llvm_version
optimize_tests = False
MINIMUM_LLVM_VERSION = 1.7

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
    if llvm_test():        
        return genllvm_compile(function, annotation, optimize=optimize_tests,
                               logging=False, **kwds)

def compile_optimized_test(function, annotation, **kwds):
    if llvm_test():        
        return genllvm_compile(function, annotation, optimize=True,
                               logging=False, **kwds)

def compile_function(function, annotation, **kwds):
    if llvm_test():
        return compile_test(function, annotation, return_fn=True, **kwds)

def compile_optimized_function(function, annotation, **kwds):
    if llvm_test():
        return compile_optimized_test(function, annotation, return_fn=True, **kwds)

