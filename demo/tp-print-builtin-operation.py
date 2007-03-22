"""

This example transparently intercepts and shows operations on 
builtin objects.  It requires the "--with-transparent-proxy" option. 

"""

from tputil import make_proxy 

def make_show_proxy(instance):
    def controller(operation):
        res = operation.delegate()
        print "proxy sees:", operation, "result=%s" %(res,)
        return res
    tproxy = make_proxy(controller, obj=instance)
    return tproxy

mydict = make_show_proxy({}) 

assert type(mydict) is dict      # this looks exactly like a dict 
mydict['hello'] = 'world'        # will print __
mydict[42] = 23 
assert mydict.pop('hello') == 'world'
assert mydict.popitem() == (42,23)


