import weakref
import UserDict
from pypy.tool.uid import Hashable


class ExtRegistryFunc(object):
    def __init__(self, compute_result_annotation, specialize_call):
        self.compute_result_annotation = compute_result_annotation
        self.specialize_call = specialize_call
    
    def get_annotation(self, type, func=None):
        assert func is not None
        from pypy.annotation import model as annmodel
        return annmodel.SomeBuiltin(self.compute_result_annotation,
                                    methodname=getattr(func, '__name__', None))

class ExtRegistryInstance(object):
    def __init__(self, compute_annotation, specialize_call, get_repr):
        self.compute_annotation = compute_annotation
        self.specialize_call = specialize_call
        self.get_repr = get_repr
    
    def get_annotation(self, type, instance=None):
        return self.compute_annotation(type, instance)

# ____________________________________________________________

class FlexibleWeakDict(UserDict.DictMixin):
    """A WeakKeyDictionary that accepts more or less anything as keys:
    weakly referenceable objects or not, hashable objects or not.
    """
    def __init__(self):
        self._regdict = {}
        self._weakdict = weakref.WeakKeyDictionary()
        self._iddict = {}

    def ref(self, key):
        try:
            hash(key)
        except TypeError:
            return self._iddict, Hashable(key)   # key is not hashable
        try:
            weakref.ref(key)
        except TypeError:
            return self._regdict, key            # key cannot be weakly ref'ed
        else:
            return self._weakdict, key           # normal case

    def __getitem__(self, key):
        d, key = self.ref(key)
        return d[key]

    def __setitem__(self, key, value):
        d, key = self.ref(key)
        d[key] = value

    def __delitem__(self, key):
        d, key = self.ref(key)
        del d[key]

    def keys(self):
        return (self._regdict.keys() +
                self._weakdict.keys() +
                [hashable.value for hashable in self._iddict])


EXT_REGISTRY_BY_VALUE = FlexibleWeakDict()
EXT_REGISTRY_BY_TYPE = weakref.WeakKeyDictionary()
EXT_REGISTRY_BY_METATYPE = weakref.WeakKeyDictionary()

def create_annotation_callable(annotation):
    from pypy.annotation import model as annmodel
    if isinstance(annotation, annmodel.SomeObject) or annotation is None:
        s_result = annotation
        def annotation(*args):
            return s_result
        
    return annotation

undefined = object()

def create_entry(compute_result_annotation=undefined, compute_annotation=None,
                 specialize_call=None, get_repr=None):
    if compute_result_annotation is not undefined:
        compute_result_annotation = create_annotation_callable(
            compute_result_annotation)
        return ExtRegistryFunc(compute_result_annotation, specialize_call)
    else:
        return ExtRegistryInstance(compute_annotation, specialize_call, 
            get_repr)

def register_value(value, **kwargs):
    assert value not in EXT_REGISTRY_BY_VALUE
    EXT_REGISTRY_BY_VALUE[value] = create_entry(**kwargs)
    return EXT_REGISTRY_BY_VALUE[value]
    
def register_type(t, **kwargs):
    assert t not in EXT_REGISTRY_BY_TYPE
    EXT_REGISTRY_BY_TYPE[t] = create_entry(**kwargs)
    return EXT_REGISTRY_BY_TYPE[t]
    
def register_metatype(t, **kwargs):
    assert t not in EXT_REGISTRY_BY_METATYPE
    EXT_REGISTRY_BY_METATYPE[t] = create_entry(**kwargs)
    return EXT_REGISTRY_BY_METATYPE[t]

def lookup_type(tp):
    try:
        return EXT_REGISTRY_BY_TYPE[tp]
    except (KeyError, TypeError):
        return EXT_REGISTRY_BY_METATYPE[type(tp)]

def is_registered_type(tp):
    try:
        lookup_type(tp)
    except KeyError:
        return False
    return True

def lookup(instance):
    try:
        return EXT_REGISTRY_BY_VALUE[instance]
    except (KeyError, TypeError):
        return lookup_type(type(instance))
        
def is_registered(instance):
    try:
        lookup(instance)
    except KeyError:
        return False
    return True
