#! /usr/bin/env python
"""
Usage:  compilemodule.py <module-name>

Compiles the PyPy extension module from  pypy/module/<module-name>/
into a regular CPython extension module.
"""
import autopath
import sys

from pypy.tool.error import debug

def compilemodule(modname, interactive=False, basepath='pypy.module'):
    "Compile a PyPy module for CPython."
    import pypy.rpython.rctypes.implementation
    from pypy.objspace.cpy.objspace import CPyObjSpace
    from pypy.objspace.cpy.function import reraise
    from pypy.objspace.cpy.ann_policy import CPyAnnotatorPolicy
    from pypy.translator.driver import TranslationDriver
    from pypy.interpreter.error import OperationError

    space = CPyObjSpace()
    space.config.translating = True
    ModuleClass = __import__(basepath + '.%s' % modname,
                             None, None, ['Module']).Module
    module = ModuleClass(space, space.wrap(modname))
    w_moduledict = module.getdict()

    def __init__(mod):
        w_mod = CPyObjSpace.W_Object(mod)
        try:
##          space.appexec([w_mod, w_moduledict],
##            '''(mod, newdict):
##                   old = mod.__dict__.copy()
##                   for key in ['__name__', '__doc__', 'RPythonError']:
##                       newdict[key] = old[key]
##                   newdict['__rpython__'] = old
##                   mod.__dict__.clear()
##                   mod.__dict__.update(newdict)
##            ''')
            # the same at interp-level:
            w_moddict = space.getattr(w_mod, space.wrap('__dict__'))
            w_old = space.call_method(w_moddict, 'copy')
            space.call_method(w_moddict, 'clear')
            space.setitem(w_moddict, space.wrap('__rpython__'), w_old)
            for key in ['__name__', '__doc__', 'RPythonError']:
                w_key = space.wrap(key)
                try:
                    w1 = space.getitem(w_old, w_key)
                except OperationError:
                    pass
                else:
                    space.setitem(w_moddict, w_key, w1)
            space.call_method(w_moddict, 'update', w_moduledict)

        except OperationError, e:
            reraise(e)

    __init__.allow_someobjects = True

    driver = TranslationDriver(extmod_name=modname)
    driver.setup(__init__, [object], policy=CPyAnnotatorPolicy(space))
    try:
        driver.proceed(['compile_c'])
    except SystemExit:
        raise
    except:
        if not interactive:
            raise
        debug(driver)
        raise SystemExit(1)
    return driver.cbuilder.c_ext_module

def main(argv):
    argvCount = len(argv)
    if argvCount < 2 or argvCount > 4:
        print >> sys.stderr, __doc__
        sys.exit(2)
    elif len(argv) == 2:
        c_ext_module = compilemodule(argv[1], interactive=True)
    elif len(argv) == 3:
        basepath = argv[2]
        c_ext_module = compilemodule(argv[1], interactive=True, basepath=basepath)
    print 'Created %r.' % (c_ext_module.__file__,)


if __name__ == '__main__':
    main(sys.argv)
