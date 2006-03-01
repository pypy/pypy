import weakref

class ExtRegistryFunc(object):
    def __init__(self, compute_result_annotation, specialize_call):
        self.compute_result_annotation = compute_result_annotation
        self.specialize_call = specialize_call
    
    def get_annotation(self, type, func=None):
        assert func is not None
        from pypy.annotation import model as annmodel
        return annmodel.SomeBuiltin(self.compute_result_annotation, methodname=func.__name__)

class ExtRegistryInstance(object):
    def __init__(self, compute_annotation, specialize_call, get_repr):
        self.compute_annotation = compute_annotation
        self.specialize_call = specialize_call
        self.get_repr = get_repr
    
    def get_annotation(self, type, instance=None):
        return self.compute_annotation(type, instance)
    
EXT_REGISTRY_BY_VALUE = weakref.WeakKeyDictionary()
EXT_REGISTRY_BY_TYPE = weakref.WeakKeyDictionary()
EXT_REGISTRY_BY_METATYPE = weakref.WeakKeyDictionary()

def create_annotation_callable(annotation):
    from pypy.annotation import model as annmodel
    if isinstance(annotation, annmodel.SomeObject):
        s_result = annotation
        def annotation(*args):
            return s_result
        
    return annotation

def create_entry(compute_result_annotation=None, compute_annotation=None,
    specialize_call=None, get_repr=None):
    if compute_result_annotation is not None:
        compute_result_annotation = create_annotation_callable(
            compute_result_annotation)
        return ExtRegistryFunc(compute_result_annotation, specialize_call)
    else:
        return ExtRegistryInstance(compute_annotation, specialize_call, 
            get_repr)

def register_value(value, **kwargs):
    EXT_REGISTRY_BY_VALUE[value] = create_entry(**kwargs)
    return EXT_REGISTRY_BY_VALUE[value]
    
def register_type(t, **kwargs):
    EXT_REGISTRY_BY_TYPE[t] = create_entry(**kwargs)
    return EXT_REGISTRY_BY_TYPE[t]
    
def register_metatype(t, **kwargs):
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
