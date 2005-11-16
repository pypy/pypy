import py
from pypy.translator.llvm.genllvm import compile_module

optimize_tests = False
MINIMUM_LLVM_VERSION = 1.6

def llvm_is_on_path():
    try:
        py.path.local.sysfind("llvm-as")
    except py.error.ENOENT: 
        return False 
    return True

def llvm_version():
    import os
    v = os.popen('llvm-as -version 2>&1').readline()
    v = ''.join([c for c in v if c.isdigit()])
    v = int(v) / 10.0
    return v

def compile_function(function, annotation, **kwds):
    if not llvm_is_on_path():
        py.test.skip("llvm not found")

    v = llvm_version()
    if v < MINIMUM_LLVM_VERSION:
        py.test.skip("llvm version not up-to-date (found %.1f, should be >= %.1f)" % (v, MINIMUM_LLVM_VERSION))

    mod = compile_module(function, annotation, optimize=optimize_tests,
                         logging=False, **kwds)
    return getattr(mod, 'pypy_' + function.func_name + "_wrapper")

def compile_module_function(function, annotation, **kwds):
    if not llvm_is_on_path():
        py.test.skip("llvm not found")

    v, minimum = llvm_version(), 1.6
    if v < minimum:
        py.test.skip("llvm version not up-to-date (found %.1f, should be >= %.1f)" % (v, minimum))
        
    mod = compile_module(function, annotation, **kwds)
    f = getattr(mod, 'pypy_' + function.func_name + "_wrapper")
    return mod, f
