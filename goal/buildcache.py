from pypy.tool import option, autopath, testit
from pypy.interpreter import gateway 
from pypy.tool.frozendict import frozendict 
import os

#######################################################
def app_triggerall():
    import sys, types # , exceptions
    k = 42
    def gen():
        yield k
        #yield (k, 1.0, 4L, [''], {}, unicode, Ellipsis) 
        try:
            raise ValueError
        except ValueError: 
            x = sys.exc_info()
        try:
            raise x[0], x[1], x[2]
        except ValueError:
            pass
            
    gen.func_code.co_name
    str({'co_name': ('f',)}), str(object.__init__.im_func.func_code)
    #"for %r" % ({'x': gen}) 
    "%02d %04f %05g %05s <%s> %r" % (1, 2.25, 2.25, 2.25, [1,2], {'x': gen})
    for x in gen():
        pass

def app_triggerexec():
    exec "i=3"
    
gateway.importall(globals())   # app_xxx() -> xxx()

#######################################################
    
def buildcache(space): 
    print "triggering cache build for %r" % space 
    triggerall(space) 
    triggerexec(space)
    space._typecache = frozendict(space._typecache) 
    space._faketypecache = frozendict(space._faketypecache) 
    space._gatewaycache = frozendict(space._gatewaycache) 
    print "cache build finished, caches are 'frozen' now"

if __name__ == '__main__': 
    space = option.objspace('std') 
    buildcache(space) 
    #testit.main(autopath.pypydir)

    testit.main(os.path.join(autopath.pypydir)) # , 'objspace', 'std'))
