import py
from pypy.translator.llvm.genllvm import compile_module

optimize_tests = False

def llvm_is_on_path():
    try:
        py.path.local.sysfind("llvm-as")
    except py.error.ENOENT: 
        return False 
    return True

def compile_function(function, annotation, **kwds):
    if not llvm_is_on_path():
        py.test.skip("llvm not found")
        
    mod = compile_module(function, annotation, optimize=optimize_tests, **kwds)
    return getattr(mod, 'pypy_' + function.func_name + "_wrapper")

def compile_module_function(function, annotation, **kwds):
    if not llvm_is_on_path():
        py.test.skip("llvm not found")
        
    mod = compile_module(function, annotation, **kwds)
    f = getattr(mod, 'pypy_' + function.func_name + "_wrapper")
    return mod, f
