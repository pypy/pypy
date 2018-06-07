# NOT_RPYTHON
# do not load _cppyy here, see _post_import_startup()
import types
import sys


# Metaclasses are needed to store C++ static data members as properties. Since
# the interp-level does not support metaclasses, they are created at app-level.
# These are the metaclass base classes:
class CPPScope(type):
    def __getattr__(self, name):
        try:
            return get_scoped_pycppitem(self, name)  # will cache on self
        except Exception as e:
            raise AttributeError("%s object has no attribute '%s' (details: %s)" %
                                 (self, name, str(e)))

class CPPMetaNamespace(CPPScope):
    def __dir__(self):
        return self.__cppdecl__.__dir__()

class CPPClass(CPPScope):
    pass

# namespace base class (class base class defined in _post_import_startup()
class CPPNamespace(object):
    __metatype__ = CPPMetaNamespace


class CPPTemplate(object):
    def __init__(self, name, scope=None):
        self._name = name
        if scope is None:
            self._scope = gbl
        else:
            self._scope = scope

    def _arg_to_str(self, arg):
      # arguments are strings representing types, types, or builtins
        if type(arg) == str:
            return arg                       # string describing type
        elif hasattr(arg, '__cppname__'):
            return arg.__cppname__           # C++ bound type
        elif arg == str:
            import _cppyy
            return _cppyy._std_string_name() # special case pystr -> C++ string
        elif isinstance(arg, type):          # builtin types
            return arg.__name__
        return str(arg)                      # builtin values

    def __call__(self, *args):
        fullname = ''.join(
            [self._name, '<', ','.join(map(self._arg_to_str, args))])
        fullname += '>'
        return getattr(self._scope, fullname)

    def __getitem__(self, *args):
        if args and type(args[0]) == tuple:
            return self.__call__(*(args[0]))
        return self.__call__(*args)


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

def get_pycppitem(final_scoped_name):
    # walk scopes recursively down from global namespace ("::") to get the
    # actual (i.e. not typedef'ed) class, triggering all necessary creation
    scope = gbl
    for name in scope_splitter(final_scoped_name):
        scope = getattr(scope, name)
    return scope
get_pycppclass = get_pycppitem     # currently no distinction, but might
                                   # in future for performance


# callbacks (originating from interp_cppyy.py) to allow interp-level to
# initiate creation of app-level classes and function
def clgen_callback(final_scoped_name):
    return get_pycppclass(final_scoped_name)

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


# construction of namespaces and classes, and their helpers
def make_module_name(scope):
    if scope:
        return scope.__module__ + '.' + scope.__name__
    return 'cppyy'

def make_cppnamespace(scope, name, decl):
    # build up a representation of a C++ namespace (namespaces are classes)

    # create a metaclass to allow properties (for static data write access)
    import _cppyy
    ns_meta = type(name+'_meta', (CPPMetaNamespace,), {})

    # create the python-side C++ namespace representation, cache in scope if given
    d = {"__cppdecl__" : decl,
         "__module__" : make_module_name(scope),
         "__cppname__" : decl.__cppname__ }
    pyns = ns_meta(name, (CPPNamespace,), d)
    if scope:
        setattr(scope, name, pyns)

    # install as modules to allow importing from (note naming: cppyy)
    sys.modules[make_module_name(pyns)] = pyns
    return pyns

def _drop_cycles(bases):
    # TODO: figure out why this is necessary?
    for b1 in bases:
        for b2 in bases:
            if not (b1 is b2) and issubclass(b2, b1):
                bases.remove(b1)   # removes lateral class
                break
    return tuple(bases)

def make_new(decl):
    def __new__(cls, *args):
        # create a place-holder only as there may be a derived class defined
        # TODO: get rid of the import and add user-land bind_object that uses
        # _bind_object (see interp_cppyy.py)
        import _cppyy
        instance = _cppyy._bind_object(0, decl, True)
        if not instance.__class__ is cls:
            instance.__class__ = cls     # happens for derived class
        return instance
    return __new__

def make_cppclass(scope, cl_name, decl):
    import _cppyy

    # get a list of base classes for class creation
    bases = [get_pycppclass(base) for base in decl.get_base_names()]
    if not bases:
        bases = [CPPInstance,]
    else:
        # it's possible that the required class now has been built if one of
        # the base classes uses it in e.g. a function interface
        try:
            return scope.__dict__[cl_name]
        except KeyError:
            pass

    # prepare dictionary for metaclass
    d_meta = {}

    # prepare dictionary for python-side C++ class representation
    def dispatch(self, m_name, signature):
        cppol = decl.__dispatch__(m_name, signature)
        return types.MethodType(cppol, self, type(self))
    d_class = {"__cppdecl__"   : decl,
         "__new__"      : make_new(decl),
         "__module__"   : make_module_name(scope),
         "__cppname__"  : decl.__cppname__,
         "__dispatch__" : dispatch,
         }

    # insert (static) methods into the class dictionary
    for m_name in decl.get_method_names():
        cppol = decl.get_overload(m_name)
        d_class[m_name] = cppol

    # add all data members to the dictionary of the class to be created, and
    # static ones also to the metaclass (needed for property setters)
    for d_name in decl.get_datamember_names():
        cppdm = decl.get_datamember(d_name)
        d_class[d_name] = cppdm
        if _cppyy._is_static_data(cppdm):
            d_meta[d_name] = cppdm

    # create a metaclass to allow properties (for static data write access)
    metabases = [type(base) for base in bases]
    metacpp = type(CPPScope)(cl_name+'_meta', _drop_cycles(metabases), d_meta)

    # create the python-side C++ class
    pycls = metacpp(cl_name, _drop_cycles(bases), d_class)

    # store the class on its outer scope
    setattr(scope, cl_name, pycls)

    # the call to register will add back-end specific pythonizations and thus
    # needs to run first, so that the generic pythonizations can use them
    import _cppyy
    _cppyy._register_class(pycls)
    _pythonize(pycls, pycls.__cppname__)
    return pycls

def make_cpptemplatetype(scope, template_name):
    return CPPTemplate(template_name, scope)


def get_scoped_pycppitem(scope, name):
    import _cppyy

    # resolve typedefs/aliases: these may cross namespaces, in which case
    # the lookup must trigger the creation of all necessary scopes
    scoped_name = (scope == gbl) and name or (scope.__cppname__+'::'+name)
    final_scoped_name = _cppyy._resolve_name(scoped_name)
    if final_scoped_name != scoped_name:
        pycppitem = get_pycppitem(final_scoped_name)
        # also store on the requested scope (effectively a typedef or pointer copy)
        setattr(scope, name, pycppitem)
        return pycppitem

    pycppitem = None

    # scopes (classes and namespaces)
    cppitem = _cppyy._scope_byname(final_scoped_name)
    if cppitem:
        if cppitem.is_namespace():
            pycppitem = make_cppnamespace(scope, name, cppitem)
        else:
            pycppitem = make_cppclass(scope, name, cppitem)

    # templates
    if not cppitem:
        cppitem = _cppyy._is_template(final_scoped_name)
        if cppitem:
            pycppitem = make_cpptemplatetype(scope, name)
            setattr(scope, name, pycppitem)

    # functions
    if not cppitem:
        try:
            cppitem = scope.__cppdecl__.get_overload(name)
            setattr(scope.__class__, name, cppitem)
            pycppitem = getattr(scope, name)      # binds function as needed
        except AttributeError:
            pass

    # data
    if not cppitem:
        try:
            cppdm = scope.__cppdecl__.get_datamember(name)
            setattr(scope, name, cppdm)
            if _cppyy._is_static_data(cppdm):
                setattr(scope.__class__, name, cppdm)
            pycppitem = getattr(scope, name)      # gets actual property value
        except AttributeError:
            pass

    if pycppitem is not None:      # pycppitem could be a bound C++ NULL, so check explicitly for Py_None
        return pycppitem

    raise AttributeError("'%s' has no attribute '%s'" % (str(scope), name))


# helper for pythonization API
def extract_namespace(name):
    # find the namespace the named class lives in, take care of templates
    tpl_open = 0
    for pos in xrange(len(name)-1, 1, -1):
        c = name[pos]

        # count '<' and '>' to be able to skip template contents
        if c == '>':
            tpl_open += 1
        elif c == '<':
            tpl_open -= 1

        # collect name up to "::"
        elif tpl_open == 0 and c == ':' and name[pos-1] == ':':
            # found the extend of the scope ... done
            return name[:pos-1], name[pos+1:]

    # no namespace; assume outer scope
    return '', name

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
    if type(slice_or_idx) == slice:
        nseq = self.__class__()
        nseq += [python_style_getitem(self, i) \
                    for i in range(*slice_or_idx.indices(len(self)))]
        return nseq
    else:
        return python_style_getitem(self, slice_or_idx)

def _pythonize(pyclass, name):
    # general note: use 'in pyclass.__dict__' rather than 'hasattr' to prevent
    # adding pythonizations multiple times in derived classes

    import _cppyy

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
    # not on vector, which is pythonized in the capi (interp-level; there is
    # also the fallback on the indexed __getitem__, but that is slower)
    if not 'vector' in name[:11] and \
            ('begin' in pyclass.__dict__ and 'end' in pyclass.__dict__):
        if _cppyy._scope_byname(name+'::iterator') or \
                _cppyy._scope_byname(name+'::const_iterator'):
            def __iter__(self):
                i = self.begin()
                while i != self.end():
                    yield i.__deref__()
                    i.__preinc__()
                i.__destruct__()
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
    if name == _cppyy._std_string_name():
        def eq(self, other):
            if type(other) == pyclass:
                return self.c_str() == other.c_str()
            else:
                return self.c_str() == other
        pyclass.__eq__  = eq
        pyclass.__str__ = pyclass.c_str

    # std::pair unpacking through iteration
    if 'std::pair' == name[:9]:
        def getitem(self, idx):
            if idx == 0: return self.first
            if idx == 1: return self.second
            raise IndexError("out of bounds")
        def return2(self):
            return 2
        pyclass.__getitem__ = getitem
        pyclass.__len__     = return2

    # user provided, custom pythonizations
    try:
        ns_name, cl_name = extract_namespace(name)
        pythonizors = _pythonizations[ns_name]
        name = cl_name
    except KeyError:
        pythonizors = _pythonizations['']   # global scope

    for p in pythonizors:
        p(pyclass, name)

def _post_import_startup():
    # _cppyy should not be loaded at the module level, as that will trigger a
    # call to space.getbuiltinmodule(), which will cause _cppyy to be loaded
    # at pypy-c startup, rather than on the "import _cppyy" statement
    import _cppyy

    # root of all proxy classes: CPPInstance in pythonify exists to combine
    # the CPPScope metaclass with the interp-level CPPInstanceBase
    global CPPInstance
    class CPPInstance(_cppyy.CPPInstanceBase):
        __metaclass__ = CPPScope
        pass

    # class generator callback
    _cppyy._set_class_generator(clgen_callback)

    # function generator callback
    _cppyy._set_function_generator(fngen_callback)

    # user interface objects
    global gbl
    gbl = make_cppnamespace(None, 'gbl', _cppyy._scope_byname(''))
    gbl.__module__  = 'cppyy'
    gbl.__doc__     = 'Global C++ namespace.'

    # pre-create std to allow direct importing
    gbl.std = make_cppnamespace(gbl, 'std', _cppyy._scope_byname('std'))

    # add move cast
    gbl.std.move = _cppyy.move

    # install a type for enums to refer to
    setattr(gbl, 'internal_enum_type_t', int)
    setattr(gbl, 'unsigned int',         int)     # if resolved

    # install for user access
    _cppyy.gbl = gbl

    # install nullptr as a unique reference
    _cppyy.nullptr = _cppyy._get_nullptr()


# user-defined pythonizations interface
_pythonizations = {'' : list()}
def add_pythonization(pythonizor, scope = ''):
    """<pythonizor> should be a callable taking two arguments: a class proxy,
    and its C++ name. It is called on each time a named class from <scope>
    (the global one by default, but a relevant C++ namespace is recommended)
    is bound.
    """
    if not callable(pythonizor):
        raise TypeError("given '%s' object is not callable" % str(pythonizor))
    try:
        _pythonizations[scope].append(pythonizor)
    except KeyError:
        _pythonizations[scope] = list()
        _pythonizations[scope].append(pythonizor)

def remove_pythonization(pythonizor, scope = ''):
    """Remove previously registered <pythonizor> from <scope>.
    """
    try:
        _pythonizations[scope].remove(pythonizor)
        return True
    except (KeyError, ValueError):
        return False
