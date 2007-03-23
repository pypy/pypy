"""

This example transparently intercepts and shows operations on 
builtin objects.  Requires the "--objspace-std-withtproxy" option. 

"""

from tputil import make_proxy 

def make_show_proxy(instance):
    def controller(operation):
        print "proxy sees:", operation
        res = operation.delegate()
        return res
    tproxy = make_proxy(controller, obj=instance)
    return tproxy

if __name__ == '__main__':
    mydict = make_show_proxy({}) 
    assert type(mydict) is dict            # this looks exactly like a dict 
    mydict['hello'] = 'world'              # will print __setitem__
    mydict[42] = 23                        # will print __setitem__
    assert mydict.pop('hello') == 'world'  # will print pop
    assert mydict.popitem() == (42,23)     # will print popitem


