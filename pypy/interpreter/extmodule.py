"""

Helpers to build extension modules.

"""

from __future__ import generators
import os, sys, types
import autopath
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.function import Function
from pypy.interpreter.module import Module


class BuiltinModule(Module):

    def __init__(self, space, modulename, w_dict=None):
        Module.__init__(self, space, space.wrap(modulename), w_dict)
        w_dict = self.w_dict

        # Compile the xxxmodule.py source file
        modulefile = os.path.join(autopath.pypydir, 'module',
                                  modulename+'module.py')
        f = open(modulefile, 'r')
        modulesource = f.read()
        f.close()
        code = compile(modulesource, modulefile, 'exec',
                       generators.compiler_flag)
        pycode = PyCode()._from_code(code)

        # Set the hooks that call back from app-level to interp-level
        w_builtins = space.w_builtins
        self.__saved_hooks = {}
        self.__file__ = os.path.join(autopath.pypydir, 'module',
                                     modulename+'interp.py')
        self.__import_interplevel = True
        newhooks = {}
        for name, hook in [('__interplevel__exec', self.app_interplevelexec),
                           ('__interplevel__eval', self.app_interpleveleval),
                           ('__import__',          self.app_interplevelimport)]:
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

        # Run the app-level module definition (xxxmodule.py)
        space.setitem(w_dict, space.wrap('__file__'), space.wrap(modulefile))
        pycode.exec_code(space, w_dict, w_dict)

        # Run the interp-level definition (xxxinterp.py)
        # if xxxmodule.py didn't do so already
        self.loadinterplevelfile()

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

    def loadinterplevelfile(self):
        try:
            self.__import_interplevel
        except AttributeError:
            pass  # already loaded
        else:
            del self.__import_interplevel
            # temporarily install an '__applevel__' pseudo-module
            sys.modules['__applevel__'] = BuiltinModule.AppModuleHack(self)
            execfile(self.__file__, self.__dict__)
            del sys.modules['__applevel__']

    def interplevelexec(self, w_codestring):
        codestring = self.space.unwrap(w_codestring)
        exec codestring in self.__dict__
        return self.space.w_None

    def interpleveleval(self, w_codestring):
        space = self.space
        codestring = space.unwrap(w_codestring)
        w_result = eval(codestring, self.__dict__)
        if w_result is None:
            w_result = space.w_None   # else assume that it is already wrapped
        return w_result

    def interplevelimport(self, w_modulename, w_globals, w_locals, w_fromlist):
        space = self.space
        w = space.wrap
        if space.is_true(space.eq(w_modulename, w('__interplevel__'))):
            self.loadinterplevelfile()
            if w_fromlist == space.w_None:
                raise ImportError, "must use 'from __interplevel__ import xx'"
            for w_name in space.unpacktuple(w_fromlist):
                name = space.unwrap(w_name)
                if hasattr(self, name):
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

    app_interplevelexec   = gateway.interp2app(interplevelexec)
    app_interpleveleval   = gateway.interp2app(interpleveleval)
    app_interplevelimport = gateway.interp2app(interplevelimport)

    class AppModuleHack:
        def __init__(self, builtinmodule):
            self.space = builtinmodule.space
            self.w_dict = builtinmodule.w_dict
        def __getattr__(self, name):
            w_func = self.space.getitem(self.w_dict, self.space.wrap(name))
            def caller(*args, **kwds):
                return self.space.call_function(w_func, *args, **kwds)
            return caller


# XXX delete everything below.


from pypy.interpreter.miscutils import InitializedClass, RwDictProxy
from pypy.interpreter.module import Module


class ExtModule(Module):
    """An empty extension module.
    Non-empty extension modules are made by subclassing ExtModule."""

    def __init__(self, space):
        Module.__init__(self, space, space.wrap(self.__name__))
        
        # to build the dictionary of the module we get all the objects
        # accessible as 'self.xxx'. Methods are bound.
        contents = {}
        for cls in self.__class__.__mro__:
            for name in cls.__dict__:
                # ignore names in '_xyz'
                if not name.startswith('_') or name.endswith('_'):
                    value = cls.__dict__[name]
                    if isinstance(value, gateway.Gateway):
                        name = value.name
                        # This hack allows a "leakage" of a private
                        # module function (starts off prefixed with
                        # 'private_'; ends up prefixed with '_')
                        if name.startswith('private_'):
                            name = name[7:]
                        value = value.__get__(self)  # get a Method
                    elif hasattr(value, '__get__'):
                        continue  # ignore CPython functions

                    # ignore tricky class-attrs we can't send from interp to app-level 
                    if name in ('__metaclass__','__module__','w_dict',):
                        continue
                    contents.setdefault(space.wrap(name), space.wrap(value))
        w_contents = space.newdict(contents.items())
        space.call_method(w_contents, 'update', self.w_dict)
        self.w_dict = w_contents
        gateway.export_values(space, self.__dict__, self.w_dict)

    __metaclass__ = InitializedClass
    def __initclass__(cls):
        gateway.exportall(RwDictProxy(cls))   # xxx() -> app_xxx()
        gateway.importall(RwDictProxy(cls))   # app_xxx() -> xxx()

    def _eval_app_source(self, sourcestring):
        """ compile/execute a sourcestring in the applevel module dictionary """
        w = self.space.wrap
        w_code = self.compile(w(sourcestring), w('<pypyinline>'), w('exec'))
        code = self.space.unwrap(w_code)
        code.exec_code(self.space, self.w_dict, self.w_dict)

        # XXX do we actually want an interp-proxy to the app-level thing here? 
        #     or no interp-level "mirror" at all? 
        co = compile(sourcestring, '<inline>','exec', 4096)
        exec co in self.__dict__
