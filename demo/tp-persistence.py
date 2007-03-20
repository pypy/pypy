"""

This small example implements a basic orthogonal persistence 
mechanism on top of PyPy's transparent proxies. 

"""
from pypymagic import transparent_proxy, get_transparent_controller
from tputil import BaseDispatcher

class PListDispatcher(BaseDispatcher):
    _changeops = ('__iadd__ __imul__ __delitem__ __setitem__ '
                  '__delslice__ __setslice__ '
                  'append extend insert pop remove reverse sort').split()

    def __init__(self, realobj, storage):
        parent = super(PListDispatcher, self)
        parent.__init__(realobj, list) 
        self._storage = storage 

    def op_default(self, realmethod, *args, **kwargs):
        res = realmethod(*args, **kwargs) 
        if realmethod.__name__ in self._changeops: 
            self.persist()
        return res 

    def persist(self):
        self._storage.dump(self.realobj) 

    @classmethod
    def load(cls, storage):
        obj = storage.load()
        return cls(obj, storage) 

def work_with_list(mylist):
    assert isinstance(mylist, list)
    assert mylist.__class__ is list 
    mylist.append(4) 
    mylist += [5,6,7]

if __name__ == '__main__': 
    import py 
    storage = py.path.local("/tmp/mystorage")
            
    somelist = [1,2,3]
    newlist = PListDispatcher(somelist, storage).proxyobj

    # here we may call into application code which can 
    # not detect easily that it is dealing with a persistent
    # object 
    work_with_list(newlist)
    del somelist, newlist 

    restoredlist = PListDispatcher.load(storage).proxyobj
    print "restored list", restoredlist
    assert restoredlist == [1,2,3,4,5,6,7]
    restoredlist *= 2
    del restoredlist 
    restoredlist = PListDispatcher.load(storage).proxyobj
    print "restored list 2", restoredlist
    assert restoredlist == [1,2,3,4,5,6,7] * 2
    
