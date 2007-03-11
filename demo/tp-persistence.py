"""

This small example implements a basic orthogonal persistence 
mechanism on top of PyPy's transparent proxies. 

"""
from pypymagic import transparent_proxy, get_transparent_controller
from types import MethodType

class PersistentListController(object):
    _changeops = ('__iadd__ __imul__ __delitem__ __setitem__ '
                  '__delslice__ __setslice__ __init__ '
                  'append extend insert pop remove reverse sort').split()

    def __init__(self, obj, storage): 
        self._obj = obj 
        self._storage = storage 
        self.persist()
        self.proxy = transparent_proxy(list, self.perform)

    def persist(self):
        self._storage.dump(self._obj) 

    def perform(self, operation, *args, **kwargs):
        result = getattr(self._obj, operation)(*args, **kwargs)
        if operation in self._changeops: 
            # state was modified, do maximally eager checkpointing 
            self.persist()
        if result is self._obj:
            # If the result is the proxied list
            # return the proxy instead.
            result = self.proxy
        elif (isinstance(result, MethodType) and
             result.im_self is self._obj):
            # Convert methods bound to the proxied list
            # to methods bound to the proxy.
            # This is to have calls to the method become calls
            # to perform.
            result = MethodType(result.im_func, self.proxy, result.im_class)
        return result

    @classmethod
    def load(cls, storage):
        obj = storage.load()
        return cls(obj, storage) 

def work_with_list(mylist):
    assert isinstance(mylist, list)
    mylist.append(4) 
    mylist += [5,6,7]

if __name__ == '__main__': 
    import py 
    storage = py.path.local("/tmp/mystorage")
            
    somelist = [1,2,3]
    newlist = PersistentListController(somelist, storage).proxy 

    # here we may call into application code which can 
    # not detect easily that it is dealing with a persistent
    # object 
    work_with_list(newlist)
    del somelist, newlist 

    restoredlist = PersistentListController.load(storage).proxy
    print "restored list", restoredlist
    print restoredlist == [1,2,3,4,5,6,7]
