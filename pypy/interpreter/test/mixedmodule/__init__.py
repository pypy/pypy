from pypy.interpreter.lazymodule import LazyModule 

class Module(LazyModule): 
    interpleveldefs = {
        '__name__' : '(space.wrap("mixedmodule"))',
        '__doc__'  : '(space.wrap("mixedmodule doc"))',
        'somefunc' : 'file1.somefunc', 
        'value'    : '(space.w_None)', 
        'path'     :   'file1.initpath(space)', 
        'cpypath'  : 'space.wrap(sys.path)'
    }

    appleveldefs = {
        'someappfunc' : 'file2_app.someappfunc', 
    }
