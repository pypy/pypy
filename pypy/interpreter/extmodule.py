"""

Helpers to build extension modules.

"""

from __future__ import generators   # for generators.compiler_flag
import os, sys, types
import autopath
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.function import Function
from pypy.interpreter.module import Module


class BuiltinModule(Module):
    """A Module subclass specifically for built-in modules."""

    def __init__(self, space, modulename, w_dict=None, sourcefile=None):
        """Load the named built-in module, by default from the source file
        'pypy/module/<name>module.py', which is app-level Python code
        with a few special features that allow it to include interp-level
        bits.  (See pypy/module/test/foomodule.py)

        The module has two parts: the interp-level objects, stored as
        attributes of 'self', and the app-level objects, stored in the
        dictionary 'self.w_dict'.  The app-level definition of the module
        runs with 'self.w_dict' as globals.  The interp-level bits are
        executed with 'self.__dict__' as globals, i.e. they can read and
        change the attributes of 'self' as global variables.
        """
        Module.__init__(self, space, space.wrap(modulename), w_dict)
        w_dict = self.w_dict

        # Compile the xxxmodule.py source file
        self.__file__ = sourcefile or os.path.join(autopath.pypydir, 'module',
                                                   modulename+'module.py')
        space.setitem(w_dict, space.wrap('__file__'),
                              space.wrap(self.__file__))
        f = open(self.__file__, 'r')
        modulesource = f.read()
        f.close()
        code = compile(modulesource, self.__file__, 'exec',
                       generators.compiler_flag)
        pycode = PyCode()._from_code(code)

        # Set the hooks that call back from app-level to interp-level
        w_builtins = space.w_builtins
        self.__saved_hooks = {}
        newhooks = {}
        
        for name, impl in [
            ('__interplevel__exec',     self.interplevelexec.im_func),
            ('__interplevel__eval',     self.interpleveleval.im_func),
            ('__interplevel__execfile', self.interplevelexecfile.im_func),
            ('__import__',              self.interplevelimport.im_func)]:
            hook = gateway.interp2app(impl).get_method(self)
            w_name = space.wrap(name)
            try:
                self.__saved_hooks[name] = space.getitem(w_builtins, w_name)
            except OperationError:
                pass
            w_hook = space.wrap(hook)
            space.setitem(w_builtins, w_name, w_hook)
            newhooks[name] = w_hook
        space.setitem(self.w_dict, space.wrap('__builtins__'),
                      space.w_builtins)

        # Temporarily install an '__applevel__' pseudo-module
        sys.modules['__applevel__'] = BuiltinModule.AppModuleHack(self)

        # Run the app-level module definition (xxxmodule.py)
        pycode.exec_code(space, w_dict, w_dict)

        # Remove the pseudo-module
        del sys.modules['__applevel__']

        # Remove/restore the hooks unless they have been modified at app-level
        for name, w_hook in newhooks.items():
            w_name = space.wrap(name)
            try:
                w_current = space.getitem(w_builtins, w_name)
            except OperationError:
                pass
            else:
                if space.is_true(space.is_(w_current, w_hook)):
                    if name in self.__saved_hooks:
                        space.setitem(w_builtins, w_name,
                                      self.__saved_hooks[name])
                    else:
                        space.delitem(w_builtins, w_name)
        del self.__saved_hooks

    def interplevelexec(self, w_codestring):
        "'exec' a string at interp-level."
        codestring = self.space.unwrap(w_codestring)
        exec codestring in self.__dict__
        return self.space.w_None

    def interpleveleval(self, w_codestring):
        """'eval' a string at interp-level.  The result must be None or
        a wrapped object, which is returned to the caller."""
        space = self.space
        codestring = space.unwrap(w_codestring)
        w_result = eval(codestring, self.__dict__)
        if w_result is None:
            w_result = space.w_None   # else assume that it is already wrapped
        return w_result

    def interplevelexecfile(self, w_filename):
        """'exec' a file at interp-level.  The file should be in the same
        directory as the xxxmodule.py source file of the module."""
        filename = self.space.unwrap(w_filename)
        filename = os.path.join(os.path.dirname(self.__file__), filename)
        execfile(filename, self.__dict__)
        return self.space.w_None

    def interplevelimport(self, w_modulename, w_globals, w_locals, w_fromlist):
        """Hook for 'from __interplevel__ import something'.
        If there is a wrapped interp-level object 'w_something', returns it.
        If there is an interp-level function 'def something(w_x, w_y...)',
        build an appropriate gateway and returns it.
        """
        space = self.space
        w = space.wrap
        if space.is_true(space.eq(w_modulename, w('__interplevel__'))):
            if w_fromlist == space.w_None:
                raise ImportError, "must use 'from __interplevel__ import xx'"
            for w_name in space.unpacktuple(w_fromlist):
                name = space.unwrap(w_name)
                if not hasattr(self, 'w_' + name):
                    f = getattr(self, name)
                    code = gateway.BuiltinCode(f, ismethod=False,
                                                  spacearg=False)
                    defs_w = list(f.func_defaults or ())
                    func = Function(space, code, self.w_dict, defs_w)
                    w_result = space.wrap(func)
                else:
                    w_result = getattr(self, 'w_' + name)
                space.setitem(self.w_dict, w_name, w_result)
            return space.wrap(self)
        else:
            return space.call_function(self.__saved_hooks['__import__'],
                                       w_modulename, w_globals,
                                       w_locals, w_fromlist)

    class AppModuleHack:
        """For interp-level convenience: 'from __applevel__ import func'
        imports the app-level function 'func' via an appropriate gateway.
        """
        def __init__(self, builtinmodule):
            self.space = builtinmodule.space
            self.w_dict = builtinmodule.w_dict
        def __getattr__(self, name):
            w_func = self.space.getitem(self.w_dict, self.space.wrap(name))
            def caller(*args, **kwds):
                return self.space.call_function(w_func, *args, **kwds)
            return caller
