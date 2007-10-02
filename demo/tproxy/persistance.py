"""

This small example implements a basic orthogonal persistence 
mechanism on top of PyPy's transparent proxies. 

"""
from tputil import make_proxy

list_changeops = set('__iadd__ __imul__ __delitem__ __setitem__ __setattr__'
                     '__delslice__ __setslice__ '
                     'append extend insert pop remove reverse sort'.split())

dict_changeops = set('__delitem__ __setitem__  __setattr__'
                     'clear pop popitem setdefault update'.split())

def ischangeop(operation): 
    """ return True if this operation is a changing operation 
        on known builtins (dicts, lists). 
    """ 
    if isinstance(operation.obj, list):
        changeops = list_changeops 
    elif isinstance(operation.obj, dict):
        changeops = dict_changeops 
    else:
        return False
    return operation.opname in changeops 

def make_persistent_proxy(instance, storage): 
    def perform(operation): 
        res = operation.delegate()
        if ischangeop(operation):
            print "persisting after:", operation 
            storage.dump(instance)
        if res is not operation.proxyobj and isinstance(res, (dict, list)):
            res = make_proxy(perform, obj=res)
        return res
    return make_proxy(perform, obj=instance) 

def load(storage):
    obj = storage.load()
    return make_persistent_proxy(obj, storage) 
    
if __name__ == '__main__': 
    import py 
    storage = py.path.local("/tmp/dictpickle")
    pdict = make_persistent_proxy({}, storage) 

    # the code below is not aware of pdict being a proxy 
    assert type(pdict) is dict
    pdict['hello'] = 'world'       
    pdict['somelist'] = []
    del pdict 

    newdict = load(storage) 
    assert newdict == {'hello': 'world', 'somelist': []}
    l = newdict['somelist']  
    l.append(1)              # this triggers persisting the whole dict 
    l.extend([2,3])          # this triggers persisting the whole dict 
    del newdict, l 
    
    newdict = load(storage)
    print newdict['somelist']   # will show [1,2,3]
