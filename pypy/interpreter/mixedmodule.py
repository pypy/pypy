from pypy.interpreter.module import Module
from pypy.interpreter.function import Function, BuiltinFunction
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root
import sys

class MixedModule(Module):
    applevel_name = None

    # The following attribute is None as long as the module has not been
    # imported yet, and when it has been, it is mod.__dict__.copy() just
    # after startup().
    w_initialdict = None
    lazy = False
    submodule_name = None

    def __init__(self, space, w_name):
        """ NOT_RPYTHON """
        Module.__init__(self, space, w_name)
        self.lazy = True
        self.lazy_initial_values_w = {}
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
                if module_cls.submodule_name is None:
                    module_cls.submodule_name = sub_name
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
            name = space.str0_w(w_submodule.w_name)
            space.setitem(self.w_dict, space.wrap(name.split(".")[-1]), w_submodule)
            space.getbuiltinmodule(name)

        if self.w_initialdict is None:
            Module.init(self, space)
            if not self.lazy and self.w_initialdict is None:
                self.save_module_content_for_future_reload()

    def save_module_content_for_future_reload(self):
        # Save the current dictionary in w_initialdict, for future
        # reloads.  This forces the dictionary if needed.
        w_dict = self.getdict(self.space)
        self.w_initialdict = self.space.call_method(w_dict, 'copy')

    @classmethod
    def get_applevel_name(cls):
        """ NOT_RPYTHON """
        if cls.applevel_name is not None:
            return cls.applevel_name
        else:
            pkgroot = cls.__module__
            return pkgroot.split('.')[-1]

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

    def setdictvalue(self, space, attr, w_value):
        if self.lazy and attr not in self.lazy_initial_values_w:
            # in lazy mode, the first time an attribute changes,
            # we save away the old (initial) value.  This allows
            # a future getdict() call to build the correct
            # self.w_initialdict, containing the initial value.
            w_initial_value = self._load_lazily(space, attr)
            self.lazy_initial_values_w[attr] = w_initial_value
        space.setitem_str(self.w_dict, attr, w_value)
        return True

    def _load_lazily(self, space, name):
        w_name = space.new_interned_str(name)
        try:
            loader = self.loaders[name]
        except KeyError:
            return None
        else:
            w_value = loader(space)
            # the idea of the following code is that all functions that are
            # directly in a mixed-module are "builtin", e.g. they get a
            # special type without a __get__
            # note that this is not just all functions that contain a
            # builtin code object, as e.g. methods of builtin types have to
            # be normal Functions to get the correct binding behaviour
            func = w_value
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
            # Force the dictionary by calling all lazy loaders now.
            # This also saves in self.w_initialdict a copy of all the
            # initial values, including if they have already been
            # modified by setdictvalue().
            for name in self.loaders:
                w_value = self.get(name)
                space.setitem(self.w_dict, space.new_interned_str(name), w_value)
            self.lazy = False
            self.save_module_content_for_future_reload()
            for key, w_initial_value in self.lazy_initial_values_w.items():
                w_key = space.new_interned_str(key)
                if w_initial_value is not None:
                    space.setitem(self.w_initialdict, w_key, w_initial_value)
                else:
                    if space.finditem(self.w_initialdict, w_key) is not None:
                        space.delitem(self.w_initialdict, w_key)
            del self.lazy_initial_values_w
        return self.w_dict

    def _cleanup_(self):
        self.getdict(self.space)
        self.w_initialdict = None
        self.startup_called = False
        self._frozen = True

    @classmethod
    def buildloaders(cls):
        """ NOT_RPYTHON """
        if not hasattr(cls, 'loaders'):
            # build a constant dictionary out of
            # applevel/interplevel definitions
            cls.loaders = loaders = {}
            pkgroot = cls.__module__
            appname = cls.get_applevel_name()
            if cls.submodule_name is not None:
                appname += '.%s' % (cls.submodule_name,)
            for name, spec in cls.interpleveldefs.items():
                loaders[name] = getinterpevalloader(pkgroot, spec)
            for name, spec in cls.appleveldefs.items():
                loaders[name] = getappfileloader(pkgroot, appname, spec)
            assert '__file__' not in loaders
            if '__doc__' not in loaders:
                loaders['__doc__'] = cls.get__doc__

    def extra_interpdef(self, name, spec):
        cls = self.__class__
        pkgroot = cls.__module__
        loader = getinterpevalloader(pkgroot, spec)
        space = self.space
        w_obj = loader(space)
        space.setattr(space.wrap(self), space.wrap(name), w_obj)

    @classmethod
    def get__doc__(cls, space):
        return space.wrap(cls.__doc__)


def getinterpevalloader(pkgroot, spec):
    """ NOT_RPYTHON """
    def ifileloader(space):
        d = {'space': space}
        # EVIL HACK (but it works, and this is not RPython :-)
        while 1:
            try:
                value = eval(spec, d)
            except NameError as ex:
                name = ex.args[0].split("'")[1]  # super-Evil
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
