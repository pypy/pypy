# NOT_RPYTHON
import cppyy


# For now, keep namespaces and classes separate as namespaces are extensible
# with info from multiple dictionaries and do not need to bother with meta
# classes for inheritance. Both are python classes, though, and refactoring
# may be in order at some point.
class CppyyScopeMeta(type):
    def __getattr__(self, name):
        try:
            return get_cppitem(self, name)  # will cache on self
        except TypeError:
            raise AttributeError("%s object has no attribute '%s'" % (self, name))

class CppyyNamespaceMeta(CppyyScopeMeta):
    pass

class CppyyClass(CppyyScopeMeta):
    pass

class CPPObject(cppyy.CPPInstance):
    __metaclass__ = CppyyClass


class CppyyTemplateType(object):
    def __init__(self, scope, name):
        self._scope = scope
        self._name = name

    def _arg_to_str(self, arg):
        if type(arg) != str:
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


def clgen_callback(name):
    return get_cppclass(name)
cppyy._set_class_generator(clgen_callback)

def make_static_function(cpptype, func_name, cppol):
    def function(*args):
        return cppol.call(None, *args)
    function.__name__ = func_name
    return staticmethod(function)

def make_method(meth_name, cppol):
    def method(self, *args):
        return cppol.call(self, *args)
    method.__name__ = meth_name
    return method


def make_data_member(cppdm):
    rettype = cppdm.get_returntype()
    if not rettype:                              # return builtin type
        cppclass = None
    else:                                        # return instance
        try:
            cppclass = get_cppclass(rettype)
        except AttributeError:
            import warnings
            warnings.warn("class %s unknown: no data member access" % rettype,
                          RuntimeWarning)
            cppclass = None
    if cppdm.is_static():
        def binder(obj):
            return cppdm.get(None, cppclass)
        def setter(obj, value):
            return cppdm.set(None, value)
    else:
        def binder(obj):
            return cppdm.get(obj, cppclass)
        setter = cppdm.set
    return property(binder, setter)


def make_cppnamespace(scope, namespace_name, cppns, build_in_full=True):
    # build up a representation of a C++ namespace (namespaces are classes)

    # create a meta class to allow properties (for static data write access)
    metans = type(CppyyNamespaceMeta)(namespace_name+'_meta', (CppyyNamespaceMeta,), {})

    if cppns:
        d = {"_cpp_proxy" : cppns}
    else:
        d = dict()
        def cpp_proxy_loader(cls):
            cpp_proxy = cppyy._type_byname(cls.__name__ != '::' and cls.__name__ or '')
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
            pyfunc = make_static_function(cppns, func_name, cppol)
            setattr(pycppns, func_name, pyfunc)

        # add all data members to the dictionary of the class to be created, and
        # static ones also to the meta class (needed for property setters)
        for dm in cppns.get_data_member_names():
            cppdm = cppns.get_data_member(dm)
            pydm = make_data_member(cppdm)
            setattr(pycppns, dm, pydm)
            setattr(metans, dm, pydm)

    return pycppns

def _drop_cycles(bases):
    # TODO: figure this out, as it seems to be a PyPy bug?!
    for b1 in bases:
        for b2 in bases:
            if not (b1 is b2) and issubclass(b2, b1):
                bases.remove(b1)   # removes lateral class
                break
    return tuple(bases)

def make_new(class_name, cpptype):
    try:
        constructor_overload = cpptype.get_overload(cpptype.type_name)
    except AttributeError:
        msg = "cannot instantiate abstract class '%s'" % class_name
        def __new__(cls, *args):
            raise TypeError(msg)
    else:
        def __new__(cls, *args):
            return constructor_overload.call(None, *args)
    return __new__

def make_cppclass(scope, class_name, final_class_name, cpptype):

    # get a list of base classes for class creation
    bases = [get_cppclass(base) for base in cpptype.get_base_names()]
    if not bases:
        bases = [CPPObject,]
    else:
        # it's technically possible that the required class now has been built
        # if one of the base classes uses it in e.g. a function interface
        try:
            return scope.__dict__[final_class_name]
        except KeyError:
            pass

    # create a meta class to allow properties (for static data write access)
    metabases = [type(base) for base in bases]
    metacpp = type(CppyyClass)(class_name+'_meta', _drop_cycles(metabases), {})

    # create the python-side C++ class representation
    d = {"_cpp_proxy" : cpptype,
         "__new__"    : make_new(class_name, cpptype),
         }
    pycpptype = metacpp(class_name, _drop_cycles(bases), d)
 
    # cache result early so that the class methods can find the class itself
    setattr(scope, final_class_name, pycpptype)

    # insert (static) methods into the class dictionary
    for meth_name in cpptype.get_method_names():
        cppol = cpptype.get_overload(meth_name)
        if cppol.is_static():
            setattr(pycpptype, meth_name, make_static_function(cpptype, meth_name, cppol))
        else:
            setattr(pycpptype, meth_name, make_method(meth_name, cppol))

    # add all data members to the dictionary of the class to be created, and
    # static ones also to the meta class (needed for property setters)
    for dm_name in cpptype.get_data_member_names():
        cppdm = cpptype.get_data_member(dm_name)
        pydm = make_data_member(cppdm)

        setattr(pycpptype, dm_name, pydm)
        if cppdm.is_static():
            setattr(metacpp, dm_name, pydm)

    _pythonize(pycpptype)
    cppyy._register_class(pycpptype)
    return pycpptype

def make_cpptemplatetype(scope, template_name):
    return CppyyTemplateType(scope, template_name)


def get_cppitem(scope, name):
    # resolve typedefs/aliases
    full_name = (scope == gbl) and name or (scope.__name__+'::'+name)
    true_name = cppyy._resolve_name(full_name)
    if true_name != full_name:
        return get_cppclass(true_name)

    pycppitem = None

    # namespaces are "open"; TODO: classes are too (template methods, inner classes ...)
    if isinstance(scope, CppyyNamespaceMeta):
        global _loaded_dictionaries_isdirty
        if _loaded_dictionaries_isdirty:  # TODO: this should be per namespace
            scope._cpp_proxy.update()     # TODO: this is currently quadratic
            _loaded_dictionaries_isdirty = False

    # classes
    cppitem = cppyy._type_byname(true_name)
    if cppitem:
        if cppitem.is_namespace():
            pycppitem = make_cppnamespace(scope, true_name, cppitem)
            setattr(scope, name, pycppitem)
        else:
            pycppitem = make_cppclass(scope, true_name, name, cppitem)

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
            pycppitem = make_static_function(scope._cpp_proxy, name, cppitem)
            setattr(scope.__class__, name, pycppitem)
            pycppitem = getattr(scope, name)      # binds function as needed
        except AttributeError:
            pass

    # data
    if not cppitem:
        try:
            cppitem = scope._cpp_proxy.get_data_member(name)
            pycppitem = make_data_member(cppitem)
            setattr(scope, name, pycppitem)
            if cppitem.is_static():
                setattr(scope.__class__, name, pycppitem)
            pycppitem = getattr(scope, name)      # gets actual property value
        except AttributeError:
            pass

    if not (pycppitem is None):   # pycppitem could be a bound C++ NULL, so check explicitly for Py_None
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

def get_cppclass(name):
    # break up the name, to walk the scopes and get the class recursively
    scope = gbl
    for part in scope_splitter(name):
        scope = getattr(scope, part)
    return scope


# pythonization by decoration (move to their own file?)
import types

def python_style_getitem(self, idx):
    # python-style indexing: check for size and allow indexing from the back
    sz = len(self)
    if idx < 0: idx = sz + idx
    if idx < sz:
        return self._getitem__unchecked(idx)
    raise IndexError('index out of range: %d requested for %s of size %d' % (idx, str(self), sz))

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

    # map size -> __len__ (generally true for STL)
    if hasattr(pyclass, 'size') and \
            not hasattr(pyclass, '__len__') and callable(pyclass.size):
        pyclass.__len__ = pyclass.size

    # map push_back -> __iadd__ (generally true for STL)
    if hasattr(pyclass, 'push_back') and not hasattr(pyclass, '__iadd__'):
        def __iadd__(self, ll):
            [self.push_back(x) for x in ll]
            return self
        pyclass.__iadd__ = __iadd__

    # map begin()/end() protocol to iter protocol
    if hasattr(pyclass, 'begin') and hasattr(pyclass, 'end'):
        try:
            # TODO: make gnu-independent
            ne = gbl.__gnu_cxx.__ne__
            def __iter__(self):
                iter = self.begin()
                while gbl.__gnu_cxx.__ne__(iter, self.end()):
                    yield iter.__deref__()
                    iter.__preinc__()
                iter.destruct()
                raise StopIteration
            pyclass.__iter__ = __iter__
        except AttributeError:
            pass

    # combine __getitem__ and __len__ to make a pythonized __getitem__
    if hasattr(pyclass, '__getitem__') and hasattr(pyclass, '__len__'):
        pyclass._getitem__unchecked = pyclass.__getitem__
        if hasattr(pyclass, '__setitem__') and hasattr(pyclass, '__iadd__'):
            pyclass.__getitem__ = python_style_sliceable_getitem
        else:
            pyclass.__getitem__ = python_style_getitem

    # string comparisons (note: CINT backend requires the simple name 'string')
    if pyclass.__name__ == 'std::basic_string<char>' or pyclass.__name__ == 'string':
        def eq(self, other):
            if type(other) == pyclass:
                return self.c_str() == other.c_str()
            else:
                return self.c_str() == other
        pyclass.__eq__ = eq

    # TODO: clean this up
    # fixup lack of __getitem__ if no const return
    if hasattr(pyclass, '__setitem__') and not hasattr(pyclass, '__getitem__'):
        pyclass.__getitem__ = pyclass.__setitem__

_loaded_dictionaries = {}
_loaded_dictionaries_isdirty = True     # should be per namespace
def load_reflection_info(name):
    try:
        return _loaded_dictionaries[name]
    except KeyError:
        dct = cppyy._load_dictionary(name)
        _loaded_dictionaries[name] = dct
        global _loaded_dictionaries_isdirty
        _loaded_dictionaries_isdirty = True
        return dct
    

# user interface objects (note the two-step of not calling type_byname here:
# creation of global functions may cause the creation of classes in the global
# namespace, so gbl must exist at that point to cache them)
gbl = make_cppnamespace(None, "::", None, False)   # global C++ namespace

# mostly for the benefit of the CINT backend, which treats std as special
gbl.std = make_cppnamespace(None, "std", None, False)

# user-defined pythonizations interface
_pythonizations = {}
def add_pythonization(class_name, callback):
    if not callable(callback):
        raise TypeError("given '%s' object is not callable" % str(callback))
    _pythonizations[class_name] = callback
