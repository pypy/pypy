import py
from pypy.interpreter.gateway import app2interp_temp 
from pypy.objspace.std import StdObjSpace 
#def getoptions(): 
#    return [....]
#
space = StdObjSpace() 

class IntTestMethod(py.test.Item): 
    def run(self, driver): 
        cls = self.extpy.resolve().im_class 
        cls.space = space 
        return super(IntTestMethod, self).run(driver) 

class AppTestMethod(py.test.Item): 
    def execute(self, target, *args): 
        func = app2interp_temp(target.im_func, target.__name__) 
        func(space, space.w_None) 

class AppClassCollector(py.test.collect.Class): 
    Item = AppTestMethod 

class IntClassCollector(py.test.collect.Class): 
    Item = IntTestMethod 
    
class Module(py.test.collect.Module): 
    def collect_class(self, extpy): 
        if extpy.check(class_=1, basestarts="Test"): 
            yield IntClassCollector(extpy) 
    def collect_appclass(self, extpy): 
        if extpy.check(class_=1, basestarts="AppTest"): 
            yield AppClassCollector(extpy) 


    
    
    
