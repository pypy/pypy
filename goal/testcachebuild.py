from pypy.tool import option, autopath, testit 
from pypy.interpreter import gateway 

#######################################################
def app_triggergenerator():
    def gen():
        yield 42
    for x in gen():
        pass
    
gateway.importall(globals())   # app_xxx() -> xxx()

#######################################################
    
def triggercachebuild(space): 
    triggergenerator(space) 

if __name__ == '__main__': 
    space = option.objspace('std') 
    #triggercachebuild(space) 
    testit.main(autopath.pypydir)
    space.allowbuildcache = False 
    testit.main(autopath.pypydir)
