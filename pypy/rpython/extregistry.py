import weakref

class ExtRegistryFunc(object):
    def __init__(self, compute_result_annotation, specialize_call):
        self.compute_result_annotation = compute_result_annotation
        self.specialize_call = specialize_call
    
    def get_annotation(self, type, func=None):
        assert func is not None
        from pypy.annotation import model as annmodel
        return annmodel.SomeBuiltin(self.compute_result_annotation, methodname=func.__name__)

class ExtRegistryType(object):
    def __init__(self, compute_annotation):
        self.compute_annotation = compute_annotation
    
    def get_annotation(self, type, instance=None):
        return self.compute_annotation(instance)

class ExtRegistryMetaType(object):
    def __init__(self, compute_annotation):
        self.compute_annotation = compute_annotation
    
    def get_annotation(self, type, instance=None):
        return self.compute_annotation(type, instance)
    
EXT_REGISTRY_BY_VALUE = weakref.WeakKeyDictionary()
EXT_REGISTRY_BY_TYPE = weakref.WeakKeyDictionary()
EXT_REGISTRY_BY_METATYPE = weakref.WeakKeyDictionary()

def register_func(func, compute_result_annotation, specialize_call=None):
    from pypy.annotation import model as annmodel
    if isinstance(compute_result_annotation, annmodel.SomeObject):
        s_result = compute_result_annotation
        def annotation(*args):
            return s_result
        
        compute_result_annotation = annotation
    
    EXT_REGISTRY_BY_VALUE[func] = ExtRegistryFunc(compute_result_annotation,
                                                    specialize_call)
    return EXT_REGISTRY_BY_VALUE[func]
    
def register_type(t, compute_annotation):
    from pypy.annotation import model as annmodel
    if isinstance(compute_annotation, annmodel.SomeObject):
        s_result = compute_annotation
        def annotation(*args):
            return s_result
        
        compute_annotation = annotation
    
    EXT_REGISTRY_BY_TYPE[t] = ExtRegistryType(compute_annotation)

    return EXT_REGISTRY_BY_TYPE[t]

def register_metatype(t, compute_annotation):
    EXT_REGISTRY_BY_METATYPE[t] = ExtRegistryMetaType(compute_annotation)

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
