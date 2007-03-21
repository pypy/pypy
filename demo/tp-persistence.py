"""

This small example implements a basic orthogonal persistence 
mechanism on top of PyPy's transparent proxies. 

"""
from pypymagic import tproxy, get_tproxy_controller
from tputil import make_instance_proxy 

list_changeops = set('__iadd__ __imul__ __delitem__ __setitem__ '
                     '__delslice__ __setslice__ '
                     'append extend insert pop remove reverse sort'.split())

def make_plist(instance, storage): 
    def perform(invocation): 
        res = invocation.perform()
        if invocation.opname in list_changeops: 
            storage.dump(instance) 
        return res
    return make_instance_proxy(instance, perform, typ=list) 

def get_plist(storage):
    obj = storage.load()
    return make_plist(obj, storage) 
    
def work_with_list(mylist):
    assert isinstance(mylist, list)
    assert mylist.__class__ is list 
    mylist.append(4) 
    mylist += [5,6,7]

if __name__ == '__main__': 
    import py 
    storage = py.path.local("/tmp/mystorage")
            
    plist = make_plist([1,2,3], storage) 
    # here we may call into application code which can 
    # not detect easily that it is dealing with a 
    # transparently persistent list 
    work_with_list(plist)
    del plist  

    restoredlist = get_plist(storage) 
    print "restored list", restoredlist
    assert restoredlist == [1,2,3,4,5,6,7]
    restoredlist *= 2
    del restoredlist 
    restoredlist = get_plist(storage) 
    print "restored list 2", restoredlist
    assert restoredlist == [1,2,3,4,5,6,7] * 2
