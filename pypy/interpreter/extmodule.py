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


# a little excercise in OOP, Python 2.2-style:

class PyBuiltinCode(pycode.PyBaseCode):
    """The code object implementing a built-in (interpreter-level) hook."""

    def __init__(self, func, boundmethod=False):
        pycode.PyBaseCode.__init__(self)
        self.func = func
        co = func.func_code
        self.co_name = func.__name__
        self.co_flags = co.co_flags
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
        self.next_arg = self.co_argcount + start

    def prepare_args(self, space, w_locals):
        args = []
        for argname in self.co_varnames[:self.co_argcount]:
            w_arg = space.getitem(w_locals, space.wrap(argname))
            args.append(w_arg)
        return args
        
    def eval_code(self, space, w_globals, w_locals):
        args = self.prepare_args(space, w_locals)
        return self.func(*args)


class PyBuiltinVarCode(PyBuiltinCode):

    def __init__(self, func, boundmethod=False):
        super(PyBuiltinVarCode, self).__init__(func, boundmethod)
        self.vararg_name = func.func_code.co_varnames[self.next_arg]
        self.co_varnames += (self.vararg_name,)
        assert self.vararg_name.endswith('_w'), "%s, arg %d: %s"%(
            func.func_name, self.co_argcount + 1, self.vararg_name)
        self.next_arg += 1

    def prepare_args(self, space, w_locals):
        args = super(PyBuiltinVarCode, self).prepare_args(space, w_locals)
        w_args = space.getitem(w_locals, space.wrap(self.vararg_name))
        args.extend(space.unpackiterable(w_args))
        return args


class PyBuiltinKwCode(PyBuiltinCode):
    def __init__(self, func, boundmethod=False):
        super(PyBuiltinKwCode, self).__init__(func, boundmethod)
        self.kwarg_name = func.func_code.co_varnames[self.next_arg]
        self.co_varnames += (self.kwarg_name,)
        assert self.kwarg_name.endswith('_w'), "%s, arg %d: %s"%(
            func.func_name, self.co_argcount + 1, self.kwarg_name)
        self.next_arg += 1

    def eval_code(self, space, w_globals, w_locals):
        args = self.prepare_args(space, w_locals)
        w_kws = space.getitem(w_locals, space.wrap(self.kwarg_name))
        kws = {}
        for w_key in space.unpackiterable(w_kws):
            kws[space.unwrap(w_key)] = space.getitem(w_kws, w_key)
        
        return self.func(*args, **kws)


class PyBuiltinVarKwCode(PyBuiltinKwCode, PyBuiltinVarCode):
    pass


def make_builtin_func(space, func, boundmethod=False):
    if func.func_code.co_flags & pycode.CO_VARARGS:
        if func.func_code.co_flags & pycode.CO_VARKEYWORDS:
            code_cls = PyBuiltinVarKwCode
        else:
            code_cls = PyBuiltinVarCode
    else:
        if func.func_code.co_flags & pycode.CO_VARKEYWORDS:
            code_cls = PyBuiltinKwCode
        else:
            code_cls = PyBuiltinCode
    code = code_cls(func, boundmethod)
    w_defaults = space.wrap(func.func_defaults)
    w_function = space.newfunction(code, space.w_None, w_defaults)
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
        for key, value in self.__class__.__dict__.items() + self.__dict__.items():
            if isinstance(value, appmethod):
                w_function = make_builtin_func(space,
                                               value.func.__get__(self),
                                               boundmethod=True)
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

    def callhelp(self, functioname, argslist):
        if self._helper is None:
            self._helper = appfile.AppHelper(self.space,
                                             self.__helper_appfile__)
        self._helper.call(functioname,argslist)
