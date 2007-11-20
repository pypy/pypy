
# This cache maps types to pointers to them.
_pointer_type_cache = {}

class PointerMetaclass(type):
    def __new__(self, name, superclass, attrs):
        res = super(PointerMetaclass, self).__new__(self, name, superclass,
                                                    attrs)
        return res

class _Pointer(object):
    __metaclass__ = PointerMetaclass

def POINTER(cls):
    try:
        return _pointer_type_cache[cls]
    except KeyError:
        pass
    if type(cls) is str:
        klass = type(_Pointer)("LP_%s" % cls,
                               (_Pointer,),
                               {})
        _pointer_type_cache[id(klass)] = klass
        return klass
    else:
        name = "LP_%s" % cls.__name__
        klass = type(_Pointer)(name,
                               (_Pointer,),
                               {'_type_': cls})
        _pointer_type_cache[cls] = klass
    return klass
