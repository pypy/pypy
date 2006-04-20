#Module helper methods
def n_functions(self): #TODO
    return 0

def function_exists(self, name):  #TODO
    return False

#ExecutionEngine helper methods
def ExecutionEngine___init__(self, mp, ForceInterpreter=False):
    return self.create(mp, ForceInterpreter)

def delete(self, fnname):
    mod = self.getModule()
    f = mod.getNamedFunction(fnname)    # XXX handle fnname not found?
    self.freeMachineCodeForFunction(f)  # still no-op on march 27th 2006
    f.eraseFromParent()
