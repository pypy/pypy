from helper import *


class Module(Wrapper):
    def __init__(self, ModuleID='mymodule'):
        self.instance = Module__init__(ModuleID)

    def getNamedFunction(self, fnname):
        f = object.__new__(Function)
        f.instance = Module_getNamedFunction(self.instance, fnname)
        return f
        

class ExistingModuleProvider(Wrapper):
    def __init__(self, M=None):
        if not M:
            M = Module()
        self.instance = ExistingModuleProvider__init__(M.instance)

ee_hack = None

class ExecutionEngine(Wrapper):
    def __init__(self, MP=None, ForceInterpreter=False):
        global ee_hack
        assert ee_hack is None, "can only make one ExecutionEngine"
        if not MP:
            MP = ExistingModuleProvider();
        self.instance = ExecutionEngine__create__(MP.instance, ForceInterpreter)
        ee_hack = self.instance #XXX how to get to the executionengine from a function?

    # XXX cast to actual Python Module (can't we automate this?)
    def getModule(self):
        m = object.__new__(Module)
        m.instance = ExecutionEngine_getModule(self.instance)
        return m

    # helpers
    def parse(self, llcode, fnname=None):
        mod = self.getModule()
        mod.ParseAssemblyString(llcode)
        mod.verifyModule()

    def delete(self, fnname):
        mod = self.getModule()
        f = mod.getNamedFunction(fnname)    # XXX handle fnname not found?
        self.freeMachineCodeForFunction(f)  # still no-op on march 27th 2006
        f.eraseFromParent()


class Function(Wrapper):
    def __init__(self):
        self.instance = Function__init__()  #XXX this get annoying quickly

    def __call__(self, *args):
        #print 'calling %s(%s)' % ('Function', ','.join([str(arg) for arg in args]))
        ft = self.getFunctionType()
        argcount = ft.getNumParams()
        #print 'argcount = ',argcounT
        if argcount != len(args):
            raise Exception("incorrect number of parameters")
        ParamType = c_longlong * argcount
        llvmvalues = ParamType()
        for i, arg in enumerate(args):
            llvmvalues[i] = to_llvm_value(arg, ft.getParamType(i)).LongVal
        pLlvmValues = cast(llvmvalues, c_void_p)
        llvmreturnvalue = ExecutionEngine_runFunction(ee_hack, self.instance, pLlvmValues)
        return to_python_value(llvmreturnvalue, ft.getReturnType())

    def getFunctionType(self):
        ft = object.__new__(FunctionType)
        ft.instance = Function_getFunctionType(self.instance)
        return ft


class GenericValue(Wrapper):
    def __init(self):
        self.instance = GenericValue__init__()


class Type(Wrapper):
    def __init(self):
        self.instance = Type__init__()

    def getContainedType(self, n):
        t = object.__new__(Type)
        t.instance = Type_getContainedType(self.instance, n)
        return t


class FunctionType(Wrapper):
    def __init(self):
        self.instance = FunctionType__init__()

    def getReturnType(self):
        t = object.__new__(Type)
        t.instance = FunctionType_getReturnType(self.instance)
        return t

    def getParamType(self, i):
        t = object.__new__(Type)
        t.instance = FunctionType_getParamType(self.instance, i)
        return t
