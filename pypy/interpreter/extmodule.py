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

    def __init__(self, func, boundmethod=False):
        pycode.PyBaseCode.__init__(self)
        self.func = func
        co = func.func_code
        self.co_name = func.__name__
        self.co_flags = co.co_flags
        # extract argument names from 'co',
        # removing 'self' and the 'w_' prefixes
        if boundmethod:
            assert co.co_varnames[0] == "self"
            start = 1
        else:
            start = 0
        argnames = []
        for argname in co.co_varnames[start:co.co_argcount]:
            assert argname.startswith('w_')
            argnames.append(argname[2:])
        self.co_varnames = tuple(argnames)
        self.co_argcount = co.co_argcount - start

    def eval_code(self, space, w_globals, w_locals):
        # this isn't quite complete: varargs and kwargs are missing
        # defaults are not here either
        args = []
        for argname in self.co_varnames:
            w_arg = space.getitem(w_locals, space.wrap(argname))
            args.append(w_arg)
        w_ret = self.func(*args)
        return w_ret

def make_builtin_func(space,func,boundmethod=False):
    code = PyBuiltinCode(func,boundmethod)
    w_function = space.newfunction(code, space.w_None, None)
    return w_function
    
class BuiltinModule:
    __appfile__ = None
    __helper_appfile__ = None

    _helper = None

    def __init__(self, space):
        self.space = space
            
    def wrap_me(self):
        w_module = self.wrap_base()
        self.wrap_appfile(w_module)
        return w_module

    def wrap_base(self):
        space = self.space
        modulename = self.__pythonname__
        w_module = space.newmodule(space.wrap(modulename))
        for key, value in self.__class__.__dict__.items():
            if isinstance(value, appmethod):
                w_function = make_builtin_func(space,value.func.__get__(self),boundmethod=True)
                space.setattr(w_module, space.wrap(key), w_function)
            elif isinstance(value, appdata):
                w_data = space.wrap(value.data)
                space.setattr(w_module, space.wrap(key), w_data)
        return w_module

    def wrap_appfile(self, w_module):
        sappfile = self.__appfile__
        if sappfile:
            space = self.space
            w_dict = space.getattr(w_module, space.wrap("__dict__"))
            appfile.AppHelper(space, sappfile, w_dict)

    def callhelp(functioname,argslist):
        if self._helper is None:
            self._helper = appfile.AppHelper(self.space,
                                             self.__helper_appfile__)
        self._helper.call(functioname,argslist)
