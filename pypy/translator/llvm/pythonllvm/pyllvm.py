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

global ee_hack

class ExecutionEngine(Wrapper):
    def __init__(self, MP=None, ForceInterpreter=False):
        if not MP:
            MP = ExistingModuleProvider();
        self.instance = ExecutionEngine__create__(MP.instance, ForceInterpreter)
        global ee_hack
        ee_hack = self.instance

    # XXX cast to actual Python Module (can't we automate this?)
    def getModule(self):
        m = object.__new__(Module)
        m.instance = ExecutionEngine_getModule(self.instance)
        return m

    # helpers
    def parse(self, llcode):
        mod = self.getModule()
        mod.ParseAssemblyString(llcode)
        mod.verifyModule()

    def delete(self, fnname):
        mod = self.getModule()
        f = mod.getNamedFunction(fnname)    # XXX handle fnname not found?
        self.freeMachineCodeForFunction(f)  # still no-op on march 27th 2006
        f.eraseFromParent()


def to_llvm_value(pythonvalue, type_):
    # XXX use the GenericValue union instead
    return pythonvalue


def to_python_value(llvmvalue, type_):
    # XXX use the GenericValue union instead
    return llvmvalue


class Function(Wrapper):
    def __init__(self):
        self.instance = Function__init__()  #XXX this get annoying quickly

    def __call__(self, *args):
        print 'calling %s(%s)' % ('Function', ','.join([str(arg) for arg in args]))
        ft = Function_getFunctionType(self.instance)
        argcount = FunctionType_getNumParams(ft)
        print 'argcount = ',argcount
        if argcount != len(args):
            raise Exception("incorrect number of parameters")
        llvmvalues = GenericValue__init__()
        for i, arg in enumerate(args):
            llvmvalues.append( to_llvm_value(arg, FunctionType_getParamType(ft, i)))
        llvmreturnvalue = ExecutionEngine_runFunction(ee_hack, self.instance, llvmvalues)
        return to_python_value(llvmreturnvalue, FunctionType_getReturnType(ft))


class GenericValue(Wrapper):
    def __init(self):
        self.instance = GenericValue__init__()


#class Instruction(Wrapper):
#    def __init__(self):
#        self.instance = Instruction__init__()
#
#
#class BasicBlock(Wrapper):
#    def __init__(self):
#        self.instance = BasicBlock__init__()
