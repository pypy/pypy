# NOT_RPYTHON
import cppyy


# For now, keep namespaces and classes separate as namespaces are extensible
# with info from multiple dictionaries and do not need to bother with meta
# classes for inheritance. Both are python classes, though, and refactoring
# may be in order at some point.
class CppyyScopeMeta(type):
    def __getattr__(self, attr):
        try:
            cppitem = get_cppitem(attr, self)
            return cppitem
        except TypeError:
            raise AttributeError("%s object has no attribute '%s'" % (self, attr))

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


def make_static_function(cpptype, func_name, cppol):
    rettype = cppol.get_returntype()
    if not rettype:                              # return builtin type
        cppclass = None
    else:                                        # return instance
        cppclass = get_cppclass(rettype)
    def function(*args):
        return cppol.call(None, cppclass, *args)
    function.__name__ = func_name
    return staticmethod(function)

def make_method(meth_name, cppol):
    rettype = cppol.get_returntype()
    if not rettype:                              # return builtin type
        cppclass = None
    else:                                        # return instance
        cppclass = get_cppclass(rettype)
    def method(self, *args):
        return cppol.call(self, cppclass, *args)
    method.__name__ = meth_name
    return method


def make_datamember(cppdm):
    rettype = cppdm.get_returntype()
    if not rettype:                              # return builtin type
        cppclass = None
    else:                                        # return instance
        try:
            cppclass = get_cppclass(rettype)
        except AttributeError, e:
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

def make_cppnamespace(namespace_name, cppns):
    d = {"_cpp_proxy" : cppns}

    # insert static methods into the "namespace" dictionary
    for func_name in cppns.get_method_names():
        cppol = cppns.get_overload(func_name)
        d[func_name] = make_static_function(cppns, func_name, cppol)

    # create a meta class to allow properties (for static data write access)
    metans = type(CppyyNamespaceMeta)(namespace_name+'_meta', (CppyyNamespaceMeta,), {})

    # add all data members to the dictionary of the class to be created, and
    # static ones also to the meta class (needed for property setters)
    for dm in cppns.get_data_member_names():
        cppdm = cppns.get_data_member(dm)
        pydm = make_datamember(cppdm)
        d[dm] = pydm
        setattr(metans, dm, pydm)

    # create the python-side C++ namespace representation
    pycppns = metans(namespace_name, (object,), d)

    # cache result and return
    _existing_cppitems[namespace_name] = pycppns
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
            return constructor_overload.call(None, cls, *args)
    return __new__

def make_cppclass(class_name, cpptype):

    # get a list of base classes for class creation
    bases = [get_cppclass(base) for base in cpptype.get_base_names()]
    if not bases:
        bases = [CPPObject,]

    # create a meta class to allow properties (for static data write access)
    metabases = [type(base) for base in bases]
    metacpp = type(CppyyClass)(class_name+'_meta', _drop_cycles(metabases), {})


    # create the python-side C++ class representation
    d = {"_cpp_proxy" : cpptype,
         "__new__"    : make_new(class_name, cpptype),
         }
    pycpptype = metacpp(class_name, _drop_cycles(bases), d)
 
    # cache result early so that the class methods can find the class itself
    _existing_cppitems[class_name] = pycpptype

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
        pydm = make_datamember(cppdm)

        setattr(pycpptype, dm_name, pydm)
        if cppdm.is_static():
            setattr(metacpp, dm_name, pydm)

    _pythonize(pycpptype)
    return pycpptype

def make_cpptemplatetype(template_name, scope):
    return CppyyTemplateType(scope, template_name)


_existing_cppitems = {}               # TODO: to merge with gbl.__dict__ (?)
def get_cppitem(name, scope=None):
    if scope and not scope is gbl:
        fullname = scope.__name__+"::"+name
    else:
        scope = gbl
        fullname = name

    # lookup class ...
    try:
        return _existing_cppitems[fullname]
    except KeyError:
        pass

    # ... if lookup failed, create (classes, templates, functions)
    pycppitem = None

    cppitem = cppyy._type_byname(fullname)
    if cppitem:
        if cppitem.is_namespace():
            pycppitem = make_cppnamespace(fullname, cppitem)
        else:
            pycppitem = make_cppclass(fullname, cppitem)
        scope.__dict__[name] = pycppitem

    if not cppitem:
        cppitem = cppyy._template_byname(fullname)
        if cppitem:
            pycppitem = make_cpptemplatetype(name, scope)
            _existing_cppitems[fullname] = pycppitem
            scope.__dict__[name] = pycppitem

    if not cppitem and isinstance(scope, CppyyNamespaceMeta):
        scope._cpp_proxy.update()  # TODO: this is currently quadratic
        cppitem = scope._cpp_proxy.get_overload(name)
        pycppitem = make_static_function(scope._cpp_proxy, name, cppitem)
        setattr(scope.__class__, name, pycppitem)
        pycppitem = getattr(scope, name)

    if pycppitem:
        _existing_cppitems[fullname] = pycppitem
        return pycppitem

    raise AttributeError("'%s' has no attribute '%s'", (str(scope), name))

get_cppclass = get_cppitem         # TODO: restrict to classes only (?)


def _pythonize(pyclass):

    # map size -> __len__ (generally true for STL)
    if hasattr(pyclass, 'size') and \
            not hasattr(pyclass,'__len__') and callable(pyclass.size):
        pyclass.__len__ = pyclass.size

    # map begin()/end() protocol to iter protocol
    if hasattr(pyclass, 'begin') and hasattr(pyclass, 'end'):
        def __iter__(self):
            iter = self.begin()
            while gbl.__gnu_cxx.__ne__(iter, self.end()):
                yield iter.__deref__()
                iter.__preinc__()
            iter.destruct()
            raise StopIteration
        pyclass.__iter__ = __iter__


_loaded_shared_libs = {}
def load_lib(name):
    try:
        return _loaded_shared_libs[name]
    except KeyError:
        lib = cppyy._load_lib(name)
        _loaded_shared_libs[name] = lib
        return lib
    

# user interface objects
gbl = make_cppnamespace("::", cppyy._type_byname(""))    # global C++ namespace
