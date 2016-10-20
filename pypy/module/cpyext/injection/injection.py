from rpython.rlib.objectmodel import we_are_translated

def inject_operators(space, name, dict_w, pto):
    if not we_are_translated() and name == 'test_module.test_mytype':
        from pypy.module.cpyext.injection._test_module import inject
        inject(space, name, dict_w, pto)

def inject_global(space, w_func, modulename, funcname):
    if (not we_are_translated() and modulename == 'injection'
          and funcname == 'make'):
        from pypy.module.cpyext.injection._test_module import inject_global
        w_func = inject_global(space, w_func, funcname)
    return w_func

def inject_module(space, w_mod, name):
    if not we_are_translated() and name == 'injection':
        from pypy.module.cpyext.injection._test_module import inject_module
        inject_module(space, w_mod, name)
