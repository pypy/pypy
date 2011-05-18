# NOT_RPYTHON
import cppyy


class CppyyClass(type):
     pass

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

def make_static_function(cpptype, name, rettype):
    if not rettype:                              # return builtin type
        def method(*args):
            return cpptype.invoke(name, *args)
    else:                                        # return instance
        cppclass = get_cppclass(rettype)
        def method(*args):
            return bind_object(cpptype.invoke(name, *args), cppclass)
    method.__name__ = name
    return staticmethod(method)

def make_method(name, rettype):
    if not rettype:                              # return builtin type
        def method(self, *args):
            return self._cppinstance.invoke(name, *args)
    else:                                        # return instance
        cppclass = get_cppclass(rettype)
        def method(self, *args):
            return bind_object(self._cppinstance.invoke(name, *args), cppclass)
    method.__name__ = name
    return method


_existing_classes = {}
def get_cppclass(name):
    # lookup class
    try:
        return _existing_classes[name]
    except KeyError:
        pass

    # if failed, create

    cpptype = cppyy._type_byname(name)
    d = {"_cppyyclass" : cpptype}

    # insert (static) methods in the class dictionary
    for f in cpptype.get_method_names():
        cppol = cpptype.get_overload(f)
        if cppol.is_static():
            d[f] = make_static_function(cpptype, f, cppol.get_returntype())
        else:
            d[f] = make_method(f, cppol.get_returntype())

    # get a list of base classes for class creation
    bases = tuple([get_cppclass(base) for base in cpptype.get_base_names()])
    if not bases:
         bases = (CppyyObject,)

    # create a meta class to allow properties (for static data write access)
    metabases = tuple([type(base) for base in bases])
    metacpp = type(CppyyClass)(name+'_meta', metabases, {})

    # add all data members to the dictionary of the class to be created, and
    # static ones also to the meta class (needed for property setters)
    for dm in cpptype.get_data_member_names():
        cppdm = cpptype.get_data_member(dm)

        d[dm] = cppdm
        if cppdm.is_static():
            setattr(metacpp, dm, cppdm)

    # create the python-side C++ class representation
    pycpptype = metacpp(name, bases, d)
 
    # cache result and return
    _existing_classes[name] = pycpptype
    return pycpptype

    # TODO: better error reporting
    # raise TypeError("no such C++ class %s" % name)


class _gbl(object):
    """Global C++ namespace, i.e. ::."""

    def __getattr__(self, attr):
        try:
            cppclass = get_cppclass(attr)
            self.__dict__[attr] = cppclass
            return cppclass
        except TypeError, e:
            import traceback
            traceback.print_exc()
            raise AttributeError("'gbl' object has no attribute '%s'" % attr)


_loaded_shared_libs = {}
def load_lib(name):
    try:
        return _loaded_shared_libs[name]
    except KeyError:
        lib = cppyy._load_lib(name)
        _loaded_shared_libs[name] = lib
        return lib
    

# user interface objects
gbl = _gbl()
