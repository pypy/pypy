from pypy.interpreter import pycode
import appfile

class appmethod(object):
    def __init__(self, func):
        self.func = func
    def __get__(self, instance, cls=None):
        return self.func.__get__(instance, cls)

class appdata(object):
    def __init__(self, data):
        self.data = data
    def __get__(self, instance, cls=None):
        return self.data


class PyBuiltinCode(pycode.PyBaseCode):
    """The code object implementing a built-in (interpreter-level) hook."""

    def __init__(self, bltinmodule, appmethod):
        pycode.PyBaseCode.__init__(self)
        self.bltinmodule = bltinmodule
        self.appmethod = appmethod
        co = appmethod.func.func_code
        self.co_name = appmethod.func.__name__
        self.co_flags = co.co_flags
        # extract argument names from 'co',
        # removing 'self' and the 'w_' prefixes
        assert co.co_varnames[0] == "self"
        argnames = []
        for argname in co.co_varnames[1:co.co_argcount]:
            assert argname.startswith('w_')
            argnames.append(argname[2:])
        self.co_varnames = tuple(argnames)
        self.co_argcount = co.co_argcount - 1

    def eval_code(self, space, w_globals, w_locals):
        # this isn't quite complete: varargs and kwargs are missing
        # defaults are not here either
        args = []
        for argname in self.co_varnames:
            w_arg = space.getitem(w_locals, space.wrap(argname))
            args.append(w_arg)
        w_ret = self.appmethod.func(self.bltinmodule, *args)
        return w_ret


class BuiltinModule:
    __appfile__ = None
    __helper_appfile__ = None

    def __init__(self, space):
        self.space = space
        if self.__helper_appfile__ is not None:
            self._helper = AppHelper(self.space, self.__helper_appfile__)
            
    def wrap_me(self):
        space = self.space
        modulename = self.__pythonname__
        w_module = space.newmodule(space.wrap(modulename))
        for key, value in self.__class__.__dict__.items():
            if isinstance(value, appmethod):
                code = PyBuiltinCode(self, value)
                w_function = space.newfunction(code, space.w_None, None)
                space.setattr(w_module, space.wrap(key), w_function)
            elif isinstance(value, appdata):
                w_data = space.wrap(value.data)
                space.setattr(w_module, space.wrap(key), w_data)
        sappfile = self.__appfile__
        if sappfile:
            w_dict = space.getattr(w_module, space.wrap("__dict__"))
            appfile.AppHelper(space, sappfile, w_dict)
        return w_module

    def callhelp(functioname,argslist):
        self._helper.call(functioname,argslist)
        
