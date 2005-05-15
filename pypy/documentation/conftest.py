import py
from py.__.documentation.conftest import Directory, DoctestText, ReSTChecker

class PyPyDoctestText(DoctestText): 
    def execute(self, module, docstring): 
        # XXX execute PyPy prompts as well 
        l = []
        for line in docstring.split('\n'): 
            if line.find('>>>>') != -1: 
                line = "" 
            l.append(line) 
        text = "\n".join(l) 
        super(PyPyDoctestText, self).execute(module, text) 

        #mod = py.std.types.ModuleType(self.fspath.basename, text) 
        #self.mergescopes(mod, scopes) 
        #failed, tot = py.std.doctest.testmod(mod, verbose=1)
        #if failed:
        #    py.test.fail("doctest %s: %s failed out of %s" %(
        #                 self.fspath, failed, tot))

class PyPyReSTChecker(ReSTChecker): 
    DoctestText = PyPyDoctestText 
    
class Directory(Directory): 
    ReSTChecker = PyPyReSTChecker 
