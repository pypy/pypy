# NOT_RPYTHON
# do not load cppyy here, see _init_pythonify()
import types, sys


# For now, keep namespaces and classes separate as namespaces are extensible
# with info from multiple dictionaries and do not need to bother with meta
# classes for inheritance. Both are python classes, though, and refactoring
# may be in order at some point.
class CppyyScopeMeta(type):
    def __getattr__(self, name):
        try:
            return get_pycppitem(self, name)  # will cache on self
        except Exception, e:
            raise AttributeError("%s object has no attribute '%s' (details: %s)" %
                                 (self, name, str(e)))

class CppyyNamespaceMeta(CppyyScopeMeta):
    def __dir__(cls):
        return cls._cpp_proxy.__dir__()

class CppyyClassMeta(CppyyScopeMeta):
    pass

# class CppyyClass defined in _init_pythonify()

class CppyyTemplateType(object):
    def __init__(self, scope, name):
        self._scope = scope
        self._name = name

    def _arg_to_str(self, arg):
        if arg == str:
            import cppyy
            arg = cppyy._std_string_name()
        elif type(arg) != str:
            arg = arg.__name__
        return arg

    def __call__(self, *args):
        fullname = ''.join(
            [self._name, '<', ','.join(map(self._arg_to_str, args))])
        if fullname[-1] == '>':
            fullname += ' >'
        else:
            fullname += '>'
        return getattr(self._scope, fullname)

    def __getitem__(self, *args):
        if args and type(args[0]) == tuple:
            return self.__call__(*(args[0]))
        return self.__call__(*args)


def clgen_callback(name):
    return get_pycppclass(name)

def fngen_callback(func, npar): # todo, some kind of arg transform spec
    if npar == 0:
        def wrapper(a0, a1):
            la0 = [a0[0], a0[1], a0[2], a0[3]]
            return func(la0)
        return wrapper
    else:
        def wrapper(a0, a1):
            la0 = [a0[0], a0[1], a0[2], a0[3]]
            la1 = [a1[i] for i in range(npar)]
            return func(la0, la1)
        return wrapper


def make_static_function(func_name, cppol):
    def function(*args):
        return cppol.call(None, *args)
    function.__name__ = func_name
    function.__doc__ = cppol.signature()
    return staticmethod(function)

def make_method(meth_name, cppol):
    def method(self, *args):
        return cppol.call(self, *args)
    method.__name__ = meth_name
    method.__doc__ = cppol.signature()
    return method


def make_cppnamespace(scope, namespace_name, cppns, build_in_full=True):
    # build up a representation of a C++ namespace (namespaces are classes)

    # create a meta class to allow properties (for static data write access)
    metans = type(CppyyNamespaceMeta)(namespace_name+'_meta', (CppyyNamespaceMeta,), {})

    if cppns:
        d = {"_cpp_proxy" : cppns}
    else:
        d = dict()
        def cpp_proxy_loader(cls):
            import cppyy
            cpp_proxy = cppyy._scope_byname(cls.__name__ != '::' and cls.__name__ or '')
            del cls.__class__._cpp_proxy
            cls._cpp_proxy = cpp_proxy
            return cpp_proxy
        metans._cpp_proxy = property(cpp_proxy_loader)

    # create the python-side C++ namespace representation, cache in scope if given
    pycppns = metans(namespace_name, (object,), d)
    if scope:
        setattr(scope, namespace_name, pycppns)

    if build_in_full:   # if False, rely on lazy build-up
        # insert static methods into the "namespace" dictionary
        for func_name in cppns.get_method_names():
            cppol = cppns.get_overload(func_name)
            pyfunc = make_static_function(func_name, cppol)
            setattr(pycppns, func_name, pyfunc)

        # add all data members to the dictionary of the class to be created, and
        # static ones also to the meta class (needed for property setters)
        for dm_name in cppns.get_datamember_names():
            cppdm = cppns.get_datamember(dm_name)
            setattr(pycppns, dm_name, cppdm)
            setattr(metans, dm_name, cppdm)

        modname = pycppns.__name__.replace('::', '.')
        sys.modules['cppyy.gbl.'+modname] = pycppns
    return pycppns

def _drop_cycles(bases):
    # TODO: figure this out, as it seems to be a PyPy bug?!
    for b1 in bases:
        for b2 in bases:
            if not (b1 is b2) and issubclass(b2, b1):
                bases.remove(b1)   # removes lateral class
                break
    return tuple(bases)

def make_new(class_name, cppclass):
    try:
        constructor_overload = cppclass.get_overload(cppclass.type_name)
    except AttributeError:
        msg = "cannot instantiate abstract class '%s'" % class_name
        def __new__(cls, *args):
            raise TypeError(msg)
    else:
        def __new__(cls, *args):
            return constructor_overload.call(None, *args)
    return __new__

def make_pycppclass(scope, class_name, final_class_name, cppclass):

    # get a list of base classes for class creation
    bases = [get_pycppclass(base) for base in cppclass.get_base_names()]
    if not bases:
        bases = [CppyyClass,]
    else:
        # it's technically possible that the required class now has been built
        # if one of the base classes uses it in e.g. a function interface
        try:
            return scope.__dict__[final_class_name]
        except KeyError:
            pass

    # create a meta class to allow properties (for static data write access)
    metabases = [type(base) for base in bases]
    metacpp = type(CppyyClassMeta)(class_name+'_meta', _drop_cycles(metabases), {})

    # create the python-side C++ class representation
    def dispatch(self, name, signature):
        cppol = cppclass.dispatch(name, signature)
        return types.MethodType(make_method(name, cppol), self, type(self))
    d = {"_cpp_proxy"   : cppclass,
         "__dispatch__" : dispatch,
         "__new__"      : make_new(class_name, cppclass),
         }
    pycppclass = metacpp(class_name, _drop_cycles(bases), d)
 
    # cache result early so that the class methods can find the class itself
    setattr(scope, final_class_name, pycppclass)

    # insert (static) methods into the class dictionary
    for meth_name in cppclass.get_method_names():
        cppol = cppclass.get_overload(meth_name)
        if cppol.is_static():
            setattr(pycppclass, meth_name, make_static_function(meth_name, cppol))
        else:
            setattr(pycppclass, meth_name, make_method(meth_name, cppol))

    # add all data members to the dictionary of the class to be created, and
    # static ones also to the meta class (needed for property setters)
    for dm_name in cppclass.get_datamember_names():
        cppdm = cppclass.get_datamember(dm_name)

        # here, setattr() can not be used, because a data member can shadow one in
        # its base class, resulting in the __set__() of its base class being called
        # by setattr(); so, store directly on the dictionary
        pycppclass.__dict__[dm_name] = cppdm
        import cppyy
        if cppyy._is_static(cppdm):     # TODO: make this a method of cppdm
            metacpp.__dict__[dm_name] = cppdm

    # the call to register will add back-end specific pythonizations and thus
    # needs to run first, so that the generic pythonizations can use them
    import cppyy
    cppyy._register_class(pycppclass)
    _pythonize(pycppclass)
    return pycppclass

def make_cpptemplatetype(scope, template_name):
    return CppyyTemplateType(scope, template_name)


def get_pycppitem(scope, name):
    import cppyy

    # resolve typedefs/aliases
    full_name = (scope == gbl) and name or (scope.__name__+'::'+name)
    true_name = cppyy._resolve_name(full_name)
    if true_name != full_name:
        return get_pycppclass(true_name)

    pycppitem = None

    # classes
    cppitem = cppyy._scope_byname(true_name)
    if cppitem:
        if cppitem.is_namespace():
            pycppitem = make_cppnamespace(scope, true_name, cppitem)
            setattr(scope, name, pycppitem)
        else:
            pycppitem = make_pycppclass(scope, true_name, name, cppitem)

    # templates
    if not cppitem:
        cppitem = cppyy._template_byname(true_name)
        if cppitem:
            pycppitem = make_cpptemplatetype(scope, name)
            setattr(scope, name, pycppitem)

    # functions
    if not cppitem:
        try:
            cppitem = scope._cpp_proxy.get_overload(name)
            pycppitem = make_static_function(name, cppitem)
            setattr(scope.__class__, name, pycppitem)
            pycppitem = getattr(scope, name)      # binds function as needed
        except AttributeError:
            pass

    # data
    if not cppitem:
        try:
            cppdm = scope._cpp_proxy.get_datamember(name)
            setattr(scope, name, cppdm)
            if cppyy._is_static(cppdm): # TODO: make this a method of cppdm
                setattr(scope.__class__, name, cppdm)
            pycppitem = getattr(scope, name)      # gets actual property value
        except AttributeError:
            pass

    if pycppitem is not None:      # pycppitem could be a bound C++ NULL, so check explicitly for Py_None
        return pycppitem

    raise AttributeError("'%s' has no attribute '%s'" % (str(scope), name))


def scope_splitter(name):
    is_open_template, scope = 0, ""
    for c in name:
        if c == ':' and not is_open_template:
            if scope:
                yield scope
                scope = ""
            continue
        elif c == '<':
            is_open_template += 1
        elif c == '>':
            is_open_template -= 1
        scope += c
    yield scope

def get_pycppclass(name):
    # break up the name, to walk the scopes and get the class recursively
    scope = gbl
    for part in scope_splitter(name):
        scope = getattr(scope, part)
    return scope


# pythonization by decoration (move to their own file?)
def python_style_getitem(self, idx):
    # python-style indexing: check for size and allow indexing from the back
    try:
        sz = len(self)
        if idx < 0: idx = sz + idx
        if idx < sz:
            return self._getitem__unchecked(idx)
        raise IndexError(
            'index out of range: %d requested for %s of size %d' % (idx, str(self), sz))
    except TypeError:
        pass
    return self._getitem__unchecked(idx)

def python_style_sliceable_getitem(self, slice_or_idx):
    if type(slice_or_idx) == types.SliceType:
        nseq = self.__class__()
        nseq += [python_style_getitem(self, i) \
                    for i in range(*slice_or_idx.indices(len(self)))]
        return nseq
    else:
        return python_style_getitem(self, slice_or_idx)

_pythonizations = {}
def _pythonize(pyclass):

    try:
        _pythonizations[pyclass.__name__](pyclass)
    except KeyError:
        pass

    # general note: use 'in pyclass.__dict__' rather than 'hasattr' to prevent
    # adding pythonizations multiple times in derived classes

    import cppyy

    # map __eq__/__ne__ through a comparison to None
    if '__eq__' in pyclass.__dict__:
        def __eq__(self, other):
            if other is None: return not self
            if not self and not other: return True
            try:
                return self._cxx_eq(other)
            except TypeError:
                return NotImplemented
        pyclass._cxx_eq = pyclass.__dict__['__eq__']
        pyclass.__eq__ = __eq__

    if '__ne__' in pyclass.__dict__:
        def __ne__(self, other):
            if other is None: return not not self
            if type(self) is not type(other): return True
            return self._cxx_ne(other)
        pyclass._cxx_ne = pyclass.__dict__['__ne__']
        pyclass.__ne__ = __ne__

    # map size -> __len__ (generally true for STL)
    if 'size' in pyclass.__dict__ and not '__len__' in pyclass.__dict__ \
           and callable(pyclass.size):
        pyclass.__len__ = pyclass.size

    # map push_back -> __iadd__ (generally true for STL)
    if 'push_back' in pyclass.__dict__ and not '__iadd__' in pyclass.__dict__:
        def __iadd__(self, ll):
            [self.push_back(x) for x in ll]
            return self
        pyclass.__iadd__ = __iadd__

    # map begin()/end() protocol to iter protocol on STL(-like) classes, but
    # not on vector, for which otherwise the user has to make sure that the
    # global == and != for its iterators are reflected, which is a hassle ...
    if not 'vector' in pyclass.__name__[:11] and \
            ('begin' in pyclass.__dict__ and 'end' in pyclass.__dict__):
        if cppyy._scope_byname(pyclass.__name__+'::iterator') or \
                cppyy._scope_byname(pyclass.__name__+'::const_iterator'):
            def __iter__(self):
                i = self.begin()
                while i != self.end():
                    yield i.__deref__()
                    i.__preinc__()
                i.destruct()
                raise StopIteration
            pyclass.__iter__ = __iter__
        # else: rely on numbered iteration

    # combine __getitem__ and __len__ to make a pythonized __getitem__
    if '__getitem__' in pyclass.__dict__ and '__len__' in pyclass.__dict__:
        pyclass._getitem__unchecked = pyclass.__getitem__
        if '__setitem__' in pyclass.__dict__ and '__iadd__' in pyclass.__dict__:
            pyclass.__getitem__ = python_style_sliceable_getitem
        else:
            pyclass.__getitem__ = python_style_getitem

    # string comparisons
    if pyclass.__name__ == cppyy._std_string_name():
        def eq(self, other):
            if type(other) == pyclass:
                return self.c_str() == other.c_str()
            else:
                return self.c_str() == other
        pyclass.__eq__  = eq
        pyclass.__str__ = pyclass.c_str

    # std::pair unpacking through iteration
    if 'std::pair' == pyclass.__name__[:9] or 'pair' == pyclass.__name__[:4]:
        def getitem(self, idx):
            if idx == 0: return self.first
            if idx == 1: return self.second
            raise IndexError("out of bounds")
        def return2(self):
            return 2
        pyclass.__getitem__ = getitem
        pyclass.__len__     = return2

_loaded_dictionaries = {}
def load_reflection_info(name):
    """Takes the name of a library containing reflection info, returns a handle
    to the loaded library."""
    try:
        return _loaded_dictionaries[name]
    except KeyError:
        import cppyy
        lib = cppyy._load_dictionary(name)
        _loaded_dictionaries[name] = lib
        return lib
    
def _init_pythonify():
    # cppyy should not be loaded at the module level, as that will trigger a
    # call to space.getbuiltinmodule(), which will cause cppyy to be loaded
    # at pypy-c startup, rather than on the "import cppyy" statement
    import cppyy

    # top-level classes
    global CppyyClass
    class CppyyClass(cppyy.CPPInstance):
        __metaclass__ = CppyyClassMeta

        def __init__(self, *args, **kwds):
            pass   # ignored, for the C++ backend, ctor == __new__ + __init__

    # class generator callback
    cppyy._set_class_generator(clgen_callback)

    # function generator callback
    cppyy._set_function_generator(fngen_callback)

    # user interface objects (note the two-step of not calling scope_byname here:
    # creation of global functions may cause the creation of classes in the global
    # namespace, so gbl must exist at that point to cache them)
    global gbl
    gbl = make_cppnamespace(None, "::", None, False)   # global C++ namespace
    gbl.__doc__ = "Global C++ namespace."

    # mostly for the benefit of the CINT backend, which treats std as special
    gbl.std = make_cppnamespace(None, "std", None, False)

    # install a type for enums to refer to
    # TODO: this is correct for C++98, not for C++11 and in general there will
    # be the same issue for all typedef'd builtin types
    setattr(gbl, 'unsigned int', int)

    # install for user access
    cppyy.gbl = gbl

    # install as modules to allow importing from
    sys.modules['cppyy.gbl'] = gbl
    sys.modules['cppyy.gbl.std'] = gbl.std

# user-defined pythonizations interface
_pythonizations = {}
def add_pythonization(class_name, callback):
    """Takes a class name and a callback. The callback should take a single
    argument, the class proxy, and is called the first time the named class
    is bound."""
    if not callable(callback):
        raise TypeError("given '%s' object is not callable" % str(callback))
    _pythonizations[class_name] = callback
