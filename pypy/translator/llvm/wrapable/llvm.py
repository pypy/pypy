# llvm.py

from wrapper import Wrapper
from ctypes import *
import llvm_helper


llvm = cdll.load('libllvm.so')
STRING = c_char_p

class ExecutionEngine(Wrapper):
    def __init__(P0,P1,P2=False):
       P0.instance = llvm_helper.ExecutionEngine___init__(P0,P1,P2)

    def create(P0,P1=False):
        return llvm.ExecutionEngine_create(P0,P1)
    create = staticmethod(create)

    def getModule(P0):
        return llvm.ExecutionEngine_getModule(P0)

    def freeMachineCodeForFunction(P0,P1):
        return llvm.ExecutionEngine_freeMachineCodeForFunction(P0,P1)

    def runFunction(P0,P1,P2):
        return llvm.ExecutionEngine_runFunction(P0,P1,P2)

class ModuleProvider(Wrapper):
    pass

class ExistingModuleProvider(Wrapper):
    def __init__(P0,P1):
       P0.instance = llvm.ExistingModuleProvider___init__(P1)

class Function(Wrapper):
    def eraseFromParent(P0):
        return llvm.Function_eraseFromParent(P0)

    def getFunctionType(P0):
        return llvm.Function_getFunctionType(P0)

class FunctionType(Wrapper):
    pass

class GenericValue(Wrapper):
    pass

class TypeID(Wrapper):
    pass

class Type(Wrapper):
    def getTypeID(P0):
        return llvm.Type_getTypeID(P0)

    def getContainedType(P0,P1):
        return llvm.Type_getContainedType(P0,P1)

    def getDescription(P0):
        return llvm.Type_getDescription(P0)

class Module(Wrapper):
    def __init__(P0,P1='mymodule'):
       P0.instance = llvm.Module___init__(P1)

    def getModuleIdentifier(P0):
        return llvm.Module_getModuleIdentifier(P0)

    def setModuleIdentifier(P0,P1='myothermodule'):
        return llvm.Module_setModuleIdentifier(P0,P1)

    def getTargetTriple(P0):
        return llvm.Module_getTargetTriple(P0)

    def setTargetTriple(P0,P1):
        return llvm.Module_setTargetTriple(P0,P1)

    def getModuleInlineAsm(P0):
        return llvm.Module_getModuleInlineAsm(P0)

    def setModuleInlineAsm(P0,P1):
        return llvm.Module_setModuleInlineAsm(P0,P1)

    def getNamedFunction(P0,P1):
        return llvm.Module_getNamedFunction(P0,P1)

    def getOrInsertFunction(P0,P1,P2):
        return llvm.Module_getOrInsertFunction(P0,P1,P2)

    def n_functions(P0):
        return llvm_helper.n_functions(P0)

    def function_exists(P0,P1='myfunction'):
        return llvm_helper.function_exists(P0,P1)

llvm.ExecutionEngine_create.restype  = ExecutionEngine
llvm.ExecutionEngine_create.argtypes = [ModuleProvider,c_long]

llvm.ExecutionEngine_getModule.restype  = Module
llvm.ExecutionEngine_getModule.argtypes = [ExecutionEngine]

llvm.ExecutionEngine_freeMachineCodeForFunction.restype  = None
llvm.ExecutionEngine_freeMachineCodeForFunction.argtypes = [ExecutionEngine,Function]

llvm.ExecutionEngine_runFunction.restype  = GenericValue
llvm.ExecutionEngine_runFunction.argtypes = [ExecutionEngine,Function,GenericValue]

llvm.ExistingModuleProvider___init__.restype  = ExistingModuleProvider
llvm.ExistingModuleProvider___init__.argtypes = [Module]

llvm.Function_eraseFromParent.restype  = None
llvm.Function_eraseFromParent.argtypes = [Function]

llvm.Function_getFunctionType.restype  = FunctionType
llvm.Function_getFunctionType.argtypes = [Function]

llvm.Type_getTypeID.restype  = TypeID
llvm.Type_getTypeID.argtypes = [Type]

llvm.Type_getContainedType.restype  = Type
llvm.Type_getContainedType.argtypes = [Type,c_long]

llvm.Type_getDescription.restype  = STRING
llvm.Type_getDescription.argtypes = [Type]

llvm.Module___init__.restype  = Module
llvm.Module___init__.argtypes = [STRING]

llvm.Module_getModuleIdentifier.restype  = STRING
llvm.Module_getModuleIdentifier.argtypes = [Module]

llvm.Module_setModuleIdentifier.restype  = None
llvm.Module_setModuleIdentifier.argtypes = [Module,STRING]

llvm.Module_getTargetTriple.restype  = STRING
llvm.Module_getTargetTriple.argtypes = [Module]

llvm.Module_setTargetTriple.restype  = None
llvm.Module_setTargetTriple.argtypes = [Module,STRING]

llvm.Module_getModuleInlineAsm.restype  = STRING
llvm.Module_getModuleInlineAsm.argtypes = [Module]

llvm.Module_setModuleInlineAsm.restype  = None
llvm.Module_setModuleInlineAsm.argtypes = [Module,STRING]

llvm.Module_getNamedFunction.restype  = Function
llvm.Module_getNamedFunction.argtypes = [Module,STRING]

llvm.Module_getOrInsertFunction.restype  = Function
llvm.Module_getOrInsertFunction.argtypes = [Module,STRING,FunctionType]



# end of llvm.py
