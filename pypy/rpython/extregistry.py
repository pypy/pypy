import weakref

class ExtRegistryFunc(object):
    def __init__(self, compute_result_annotation):
        self.compute_result_annotation = compute_result_annotation
    
    def get_annotation(self, func):
        from pypy.annotation import model as annmodel
        return annmodel.SomeBuiltin(self.compute_result_annotation, methodname=func.__name__)

class ExtRegistryType(object):
    def __init__(self, compute_annotation):
        self.compute_annotation = compute_annotation
    
    def get_annotation(self, instance=None):
        return self.compute_annotation(instance)
    
EXT_REGISTRY_BY_VALUE = weakref.WeakKeyDictionary()
EXT_REGISTRY_BY_TYPE = weakref.WeakKeyDictionary()
EXT_REGISTRY_BY_METATYPE = weakref.WeakKeyDictionary()

def register_func(func, compute_result_annotation):
    from pypy.annotation import model as annmodel
    if isinstance(compute_result_annotation, annmodel.SomeObject):
        s_result = compute_result_annotation
        def annotation(*args):
            return s_result
        
        compute_result_annotation = annotation
    
    EXT_REGISTRY_BY_VALUE[func] = ExtRegistryFunc(compute_result_annotation)
    
def register_type(t, compute_annotation):
    from pypy.annotation import model as annmodel
    if isinstance(compute_annotation, annmodel.SomeObject):
        s_result = compute_annotation
        def annotation(*args):
            return s_result
        
        compute_annotation = annotation
    
    EXT_REGISTRY_BY_TYPE[t] = ExtRegistryType(compute_annotation)

def register_metatype(t, compute_annotation):
    EXT_REGISTRY_BY_METATYPE[t] = ExtRegistryType(compute_annotation)
    