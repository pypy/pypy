from pypy.interpreter.module import Module
from pypy.interpreter.function import Function, BuiltinFunction
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root
import os, sys

import inspect

class MixedModule(Module):

    NOT_RPYTHON_ATTRIBUTES = ['loaders']

    applevel_name = None
    expose__file__attribute = True

    # The following attribute is None as long as the module has not been
    # imported yet, and when it has been, it is mod.__dict__.items() just
    # after startup().
    w_initialdict = None

    def __init__(self, space, w_name):
        """ NOT_RPYTHON """
        Module.__init__(self, space, w_name)
        self.lazy = True
        self.__class__.buildloaders()
        self.loaders = self.loaders.copy()    # copy from the class to the inst
        self.submodules_w = []

    def install(self):
        """NOT_RPYTHON: install this module, and it's submodules into
        space.builtin_modules"""
        Module.install(self)
        if hasattr(self, "submodules"):
            space = self.space
            name = space.unwrap(self.w_name)
            for sub_name, module_cls in self.submodules.iteritems():
                module_name = space.wrap("%s.%s" % (name, sub_name))
                m = module_cls(space, module_name)
                m.install()
                self.submodules_w.append(m)

    def init(self, space):
        """This is called each time the module is imported or reloaded
        """
        if self.w_initialdict is not None:
            # the module was already imported.  Refresh its content with
            # the saved dict, as done with built-in and extension modules
            # on CPython.
            space.call_method(self.w_dict, 'update', self.w_initialdict)

        for w_submodule in self.submodules_w:
            name = space.str_w(w_submodule.w_name)
            space.setitem(self.w_dict, space.wrap(name.split(".")[-1]), w_submodule)
            space.getbuiltinmodule(name)

        if self.w_initialdict is None:
            Module.init(self, space)
            if not self.lazy and self.w_initialdict is None:
                self.w_initialdict = space.call_method(self.w_dict, 'items')


    def get_applevel_name(cls):
        """ NOT_RPYTHON """
        if cls.applevel_name is not None:
            return cls.applevel_name
        else:
            pkgroot = cls.__module__
            return pkgroot.split('.')[-1]
    get_applevel_name = classmethod(get_applevel_name)

    def get(self, name):
        space = self.space
        w_value = self.getdictvalue(space, name)
        if w_value is None:
            raise OperationError(space.w_AttributeError, space.wrap(name))
        return w_value

    def call(self, name, *args_w):
        w_builtin = self.get(name)
        return self.space.call_function(w_builtin, *args_w)

    def getdictvalue(self, space, name):
        w_value = space.finditem_str(self.w_dict, name)
        if self.lazy and w_value is None:
            return self._load_lazily(space, name)
        return w_value

    def _load_lazily(self, space, name):
        w_name = space.new_interned_str(name)
        try:
            loader = self.loaders[name]
        except KeyError:
            return None
        else:
            w_value = loader(space)
            func = space.interpclass_w(w_value)
            # the idea of the following code is that all functions that are
            # directly in a mixed-module are "builtin", e.g. they get a
            # special type without a __get__
            # note that this is not just all functions that contain a
            # builtin code object, as e.g. methods of builtin types have to
            # be normal Functions to get the correct binding behaviour
            if (isinstance(func, Function) and
                type(func) is not BuiltinFunction):
                try:
                    bltin = func._builtinversion_
                except AttributeError:
                    bltin = BuiltinFunction(func)
                    bltin.w_module = self.w_name
                    func._builtinversion_ = bltin
                    bltin.name = name
                w_value = space.wrap(bltin)
            space.setitem(self.w_dict, w_name, w_value)
            return w_value


    def getdict(self, space):
        if self.lazy:
            for name in self.loaders:
                w_value = self.get(name)
                space.setitem(self.w_dict, space.new_interned_str(name), w_value)
            self.lazy = False
            self.w_initialdict = space.call_method(self.w_dict, 'items')
        return self.w_dict

    def _freeze_(self):
        self.getdict(self.space)
        self.w_initialdict = None
        self.startup_called = False
        self._frozen = True
        # hint for the annotator: Modules can hold state, so they are
        # not constant
        return False

    def buildloaders(cls):
        """ NOT_RPYTHON """
        if not hasattr(cls, 'loaders'):
            # build a constant dictionary out of
            # applevel/interplevel definitions
            cls.loaders = loaders = {}
            pkgroot = cls.__module__
            appname = cls.get_applevel_name()
            for name, spec in cls.interpleveldefs.items():
                loaders[name] = getinterpevalloader(pkgroot, spec)
            for name, spec in cls.appleveldefs.items():
                loaders[name] = getappfileloader(pkgroot, appname, spec)
            assert '__file__' not in loaders
            if cls.expose__file__attribute:
                loaders['__file__'] = cls.get__file__
            if '__doc__' not in loaders:
                loaders['__doc__'] = cls.get__doc__

    buildloaders = classmethod(buildloaders)

    def extra_interpdef(self, name, spec):
        cls = self.__class__
        pkgroot = cls.__module__
        loader = getinterpevalloader(pkgroot, spec)
        space = self.space
        w_obj = loader(space)
        space.setattr(space.wrap(self), space.wrap(name), w_obj)

    def get__file__(cls, space):
        """ NOT_RPYTHON.
        return the __file__ attribute of a MixedModule
        which is the root-directory for the various
        applevel and interplevel snippets that make
        up the module.
        """
        try:
            fname = cls._fname
        except AttributeError:
            pkgroot = cls.__module__
            mod = __import__(pkgroot, None, None, ['__doc__'])
            fname = mod.__file__
            assert os.path.basename(fname).startswith('__init__.py')
            # make it clear that it's not really the interp-level module
            # at this path that we are seeing, but an app-level version of it
            fname = os.path.dirname(fname)
            cls._fname = fname
        return space.wrap(fname)

    get__file__ = classmethod(get__file__)

    def get__doc__(cls, space):
        return space.wrap(cls.__doc__)
    get__doc__ = classmethod(get__doc__)


def getinterpevalloader(pkgroot, spec):
    """ NOT_RPYTHON """
    def ifileloader(space):
        d = {'space' : space}
        # EVIL HACK (but it works, and this is not RPython :-)
        while 1:
            try:
                value = eval(spec, d)
            except NameError, ex:
                name = ex.args[0].split("'")[1] # super-Evil
                if name in d:
                    raise   # propagate the NameError
                try:
                    d[name] = __import__(pkgroot+'.'+name, None, None, [name])
                except ImportError:
                    etype, evalue, etb = sys.exc_info()
                    try:
                        d[name] = __import__(name, None, None, [name])
                    except ImportError:
                        # didn't help, re-raise the original exception for
                        # clarity
                        raise etype, evalue, etb
            else:
                #print spec, "->", value
                if hasattr(value, 'func_code'):  # semi-evil
                    return space.wrap(gateway.interp2app(value))

                try:
                    is_type = issubclass(value, W_Root)  # pseudo-evil
                except TypeError:
                    is_type = False
                if is_type:
                    return space.gettypefor(value)

                assert isinstance(value, W_Root), (
                    "interpleveldef %s.%s must return a wrapped object "
                    "(got %r instead)" % (pkgroot, spec, value))
                return value
    return ifileloader

applevelcache = {}
def getappfileloader(pkgroot, appname, spec):
    """ NOT_RPYTHON """
    # hum, it's a bit more involved, because we usually
    # want the import at applevel
    modname, attrname = spec.split('.')
    impbase = pkgroot + '.' + modname
    try:
        app = applevelcache[impbase]
    except KeyError:
        import imp
        pkg = __import__(pkgroot, None, None, ['__doc__'])
        file, fn, (suffix, mode, typ) = imp.find_module(modname, pkg.__path__)
        assert typ == imp.PY_SOURCE
        source = file.read()
        file.close()
        if fn.endswith('.pyc') or fn.endswith('.pyo'):
            fn = fn[:-1]
        app = gateway.applevel(source, filename=fn, modname=appname)
        applevelcache[impbase] = app

    def afileloader(space):
        return app.wget(space, attrname)
    return afileloader
