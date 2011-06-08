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
            self.__dict__[attr] = cppitem
            return cppitem
        except TypeError:
            raise AttributeError("%s object has no attribute '%s'" % (self, attr))

class CppyyNamespaceMeta(CppyyScopeMeta):
    pass

class CppyyClass(CppyyScopeMeta):
    pass


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

class CppyyObject(object):
    __metaclass__ = CppyyClass

    def __init__(self, *args):
        self._cppinstance = self._cppyyclass.construct(*args)
        
    def destruct(self):
        self._cppinstance.destruct()


def bind_object(cppobj, cppclass):
    if cppobj is None:
        return None
    bound_obj = object.__new__(cppclass)
    bound_obj._cppinstance = cppobj
    return bound_obj

def make_static_function(cpptype, func_name, cppol):
    rettype = cppol.get_returntype()
    if not rettype:                              # return builtin type
        def method(*args):
            return cpptype.invoke(cppol, *args)
    else:                                        # return instance
        cppclass = get_cppclass(rettype)
        def method(*args):
            return bind_object(cpptype.invoke(cppol, *args), cppclass)
    method.__name__ = func_name
    return staticmethod(method)

def make_method(meth_name, cppol):
    rettype = cppol.get_returntype()
    if not rettype:                              # return builtin type
        def method(self, *args):
            return self._cppinstance.invoke(cppol, *args)
    else:                                        # return instance
        cppclass = get_cppclass(rettype)
        def method(self, *args):
            return bind_object(self._cppinstance.invoke(cppol, *args), cppclass)
    method.__name__ = meth_name
    return method


def make_cppnamespace(namespace_name, cppns):
    d = {}

    # insert static methods into the "namespace" dictionary
    for func_name in cppns.get_method_names():
        cppol = cppns.get_overload(f)
        d[func_name] = make_static_function(cppns, func_name, cppol)

    # create a meta class to allow properties (for static data write access)
    metans = type(CppyyNamespaceMeta)(namespace_name+'_meta', (CppyyNamespaceMeta,), {})

    # add all data members to the dictionary of the class to be created, and
    # static ones also to the meta class (needed for property setters)
    for dm in cppns.get_data_member_names():
        cppdm = cppns.get_data_member(dm)
        d[dm] = cppdm
        setattr(metans, dm, cppdm)

    # create the python-side C++ namespace representation
    pycppns = metans(namespace_name, (object,), d)

    # cache result and return
    _existing_cppitems[namespace_name] = pycppns
    return pycppns

def make_cppclass(class_name, cpptype):

    # get a list of base classes for class creation
    bases = tuple([get_cppclass(base) for base in cpptype.get_base_names()])
    if not bases:
        bases = (CppyyObject,)

    # create a meta class to allow properties (for static data write access)
    metabases = tuple([type(base) for base in bases])
    metacpp = type(CppyyClass)(class_name+'_meta', metabases, {})

    # create the python-side C++ class representation
    d = {"_cppyyclass" : cpptype}
    pycpptype = metacpp(class_name, bases, d)
 
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

        setattr(pycpptype, dm_name, cppdm)
        if cppdm.is_static():
            setattr(metacpp, dm_name, cppdm)

    return pycpptype

def make_cpptemplatetype(template_name, scope):
    return CppyyTemplateType(scope, template_name)


_existing_cppitems = {}               # to merge with gbl.__dict__ (?)
def get_cppitem(name, scope=None):
    if scope and not scope is gbl:
        fullname = scope.__name__+"::"+name
    else:
        fullname = name

    # lookup class ...
    try:
        return _existing_cppitems[fullname]
    except KeyError:
        pass

    # ... if lookup failed, create
    pycppitem = None
    cppitem = cppyy._type_byname(fullname)
    if cppitem:
        if cppitem.is_namespace():
            pycppitem = make_cppnamespace(fullname, cppitem)
        else:
            pycppitem = make_cppclass(fullname, cppitem)
    else:
        cppitem = cppyy._template_byname(fullname)
        if cppitem:
            pycppitem = make_cpptemplatetype(name, scope)
            _existing_cppitems[fullname] = pycppitem

    if pycppitem:
        _existing_cppitems[fullname] = pycppitem
        return pycppitem

    raise AttributeError("'%s' has no attribute '%s'", (str(scope), name))

get_cppclass = get_cppitem         # TODO: restrict to classes only (?)


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
