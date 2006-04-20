#!/usr/bin/env python

from wrapable import *
from ctypes import *


# All the classes we wrap in the module...
Global                 = Wglobal()
ExecutionEngine        = Wclass('ExecutionEngine'       , [])
ModuleProvider         = Wclass('ModuleProvider'        , [])
ExistingModuleProvider = Wclass('ExistingModuleProvider', [ModuleProvider])
Function               = Wclass('Function'              , [])
FunctionType           = Wclass('FunctionType'          , [])
GenericValue           = Wclass('GenericValue'          , [])
TypeID                 = Enum('TypeID'                  , [])
Type                   = Wclass('Type'                  , [])
Module                 = Wclass('Module'                , [])

# Helper functions
as_c_string = CppCast('as_c_string', STRING)
as_std_string = CppCast('as_std_string', STRING)
as_vector_GenericValue = CppCast('as_vector_GenericValue', GenericValue)

# All the functions (XXX not working/output yet)
Global\
    .add(Wfunction(None , 'ParseAssemblyString', [Module, STRING]))\
    .add(Wfunction(c_int, 'verifyModule'       , [Module]))

# All the methods each class contains...
ExecutionEngine\
    .add(Wctor(ExecutionEngine, [ModuleProvider,c_int], [False],\
               'llvm_helper.ExecutionEngine___init__'))\
    .add(Wstaticmethod(ExecutionEngine, 'create', [ModuleProvider,c_int], [False]))\
    .add(Wmethod(Ref(Module)         , 'getModule', []))\
    .add(Wmethod(None                , 'freeMachineCodeForFunction', [Function]))\
    .add(Wmethod(Inst(GenericValue)  , 'runFunction', [Function,as_vector_GenericValue]))

ExistingModuleProvider\
    .add(Wctor(ExistingModuleProvider, [Module]))

Function\
    .add(Wmethod(None        , 'eraseFromParent', []))\
    .add(Wmethod(FunctionType, 'getFunctionType', []))
    
Type\
    .add(Wmethod(TypeID      , 'getTypeID', []))\
    .add(Wmethod(Type        , 'getContainedType', [c_int]))\
    .add(Wmethod(as_c_string , 'getDescription', []))

Module\
    .add(Wctor(Module, [as_std_string], ['mymodule']))\
    .add(Wmethod(as_c_string , 'getModuleIdentifier', []))\
    .add(Wmethod(None        , 'setModuleIdentifier', [STRING], ['myothermodule']))\
    .add(Wmethod(as_c_string , 'getTargetTriple', []))\
    .add(Wmethod(None        , 'setTargetTriple', [STRING]))\
    .add(Wmethod(as_c_string , 'getModuleInlineAsm', []))\
    .add(Wmethod(None        , 'setModuleInlineAsm', [STRING]))\
    .add(Wmethod(Function    , 'getNamedFunction', [STRING]))\
    .add(Wmethod(Function    , 'getOrInsertFunction', [STRING, FunctionType]))\
    .add(Wmethod(c_int       , 'llvm_helper.n_functions', []))\
    .add(Wmethod(c_int       , 'llvm_helper.function_exists', [STRING], ['myfunction']))

# Create the module...
Wroot('llvm')\
    .include('llvm/Module.h')\
    .include('llvm/ModuleProvider.h')\
    .include('llvm/Function.h')\
    .include('llvm/DerivedTypes.h')\
    .include('llvm/Type.h')\
    .include('llvm/Analysis/Verifier.h')\
    .include('llvm/ExecutionEngine/ExecutionEngine.h')\
    .include('llvm/ExecutionEngine/GenericValue.h')\
    .include('llvm_helper.py')\
    .add(Global)\
    .add(ExecutionEngine)\
    .add(ModuleProvider)\
    .add(ExistingModuleProvider)\
    .add(Function)\
    .add(FunctionType)\
    .add(GenericValue)\
    .add(TypeID)\
    .add(Type)\
    .add(Module)\
    .create()
