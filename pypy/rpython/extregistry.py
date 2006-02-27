class ExtRegistryFunc:
    def __init__(self, compute_result_annotation):
        self.compute_result_annotation = compute_result_annotation
    
    def get_annotation(self, func):
        from pypy.annotation import model as annmodel
        return annmodel.SomeBuiltin(self.compute_result_annotation, methodname=func.__name__)
    
EXT_REGISTRY_BY_VALUE = {}
EXT_REGISTRY_BY_TYPE = {}

def register_func(func, compute_result_annotation):
    from pypy.annotation import model as annmodel
    if isinstance(compute_result_annotation, annmodel.SomeObject):
        s_result = compute_result_annotation
        def annotation(*args):
            return s_result
        
        compute_result_annotation = annotation
    
    EXT_REGISTRY_BY_VALUE[func] = ExtRegistryFunc(compute_result_annotation)
    
def register_type():
    pass

