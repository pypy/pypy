# NOT_RPYTHON
import cppyy


class CppyyClass(type):
     pass

class CppyyObject(object):
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
    if rettype is None:
        def method(*args):
            return cpptype.invoke(name, *args)
    else:
        cppclass = get_cppclass(rettype)
        def method(*args):
            return bind_object(cpptype.invoke(name, *args), cppclass)
    method.__name__ = name
    return staticmethod(method)

def make_method(name, rettype):
    if rettype is None:                          # return builtin type
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
    # TODO: handle base classes
    cpptype = cppyy._type_byname(name)
    d = {"_cppyyclass" : cpptype}
    for f in cpptype.get_method_names():
        cppol = cpptype.get_overload(f)
        if cppol.is_static():
            d[f] = make_static_function(cpptype, f, cppol.get_returntype())
        else:
            d[f] = make_method(f, cppol.get_returntype())

    for dm in cpptype.get_data_member_names():
         d[dm] = cpptype.get_data_member(dm)

    pycpptype = CppyyClass(name, (CppyyObject,), d)

    return pycpptype

#    raise TypeError("no such C++ class %s" % name)


class _gbl(object):
    """Global C++ namespace, i.e. ::."""

    def __getattr__(self, attr):
        try:
            cppclass = get_cppclass(attr)
            self.__dict__[attr] = cppclass
            return cppclass
        except TypeError, e:
            import traceback
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
