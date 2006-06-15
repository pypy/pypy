#! /usr/bin/env python
"""
Usage:  compilemodule.py <module-name>

Compiles the PyPy extension module from  pypy/module/<module-name>/
into a regular CPython extension module.
"""
import autopath
import sys


def compilemodule(modname, interactive=False):
    "Compile a PyPy module for CPython."
    import pypy.rpython.rctypes.implementation
    from pypy.objspace.cpy.objspace import CPyObjSpace
    from pypy.objspace.cpy.function import reraise
    from pypy.objspace.cpy.ann_policy import CPyAnnotatorPolicy
    from pypy.translator.driver import TranslationDriver
    from pypy.interpreter.error import OperationError

    space = CPyObjSpace(translating=True)
    ModuleClass = __import__('pypy.module.%s' % modname,
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


def debug(drv):
    # XXX unify some code with pypy.translator.goal.translate
    from pypy.translator.tool.pdbplus import PdbPlusShow
    from pypy.translator.driver import log
    t = drv.translator
    class options:
        huge = 100

    tb = None
    import traceback
    errmsg = ["Error:\n"]
    exc, val, tb = sys.exc_info()
    errmsg.extend([" %s" % line for line in traceback.format_exception(exc, val, tb)])
    block = getattr(val, '__annotator_block', None)
    if block:
        class FileLike:
            def write(self, s):
                errmsg.append(" %s" % s)
        errmsg.append("Processing block:\n")
        t.about(block, FileLike())
    log.ERROR(''.join(errmsg))

    log.event("start debugger...")

    def server_setup(port=None):
        if port is not None:
            from pypy.translator.tool.graphserver import run_async_server
            serv_start, serv_show, serv_stop = self.async_server = run_async_server(t, options, port)
            return serv_start, serv_show, serv_stop
        else:
            from pypy.translator.tool.graphserver import run_server_for_inprocess_client
            return run_server_for_inprocess_client(t, options)

    pdb_plus_show = PdbPlusShow(t)
    pdb_plus_show.start(tb, server_setup, graphic=True)


def main(argv):
    if len(argv) != 2:
        print >> sys.stderr, __doc__
        sys.exit(2)
    c_ext_module = compilemodule(argv[1], interactive=True)
    print 'Created %r.' % (c_ext_module.__file__,)


if __name__ == '__main__':
    main(sys.argv)
