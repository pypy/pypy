from helper import *

class Module(Wrapper):
    def __init__(self, ModuleID='mymodule'):
        self.instance = Module__init__(ModuleID)

class ModuleProvider(Wrapper):
    pass

class ExistingModuleProvider(ModuleProvider):
    def __init__(self, M=None):
        if not M:
            M = Module()
        self.instance = ExistingModuleProvider__init__(M.instance)

class ExecutionEngine(Wrapper):
    def __init__(self, MP=None, ForceInterpreter=False):
        if not MP:
            MP = ExistingModuleProvider();
        self.instance = ExecutionEngine__create__(MP.instance, ForceInterpreter)

    def getModule(self):
        m = object.__new__(Module)
        m.instance = ExecutionEngine_getModule(self.instance)
        return m

    def parse(self, llcode):
        self.getModule().ParseAssemblyString(llcode)
        self.getModule().verifyModule()
