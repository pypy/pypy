import os
from pypy.translator.cli.dotnet import CLR
from pypy.translator.cli import dotnet
System = CLR.System
Utils = CLR.pypy.runtime.Utils
AutoSaveAssembly = CLR.pypy.runtime.AutoSaveAssembly
MethodAttributes = System.Reflection.MethodAttributes
TypeAttributes = System.Reflection.TypeAttributes

class AbstractMethodWrapper:
    
    def get_il_generator(self):
        raise NotImplementedError

    def create_delegate(self, delegatetype, consts):
        raise NotImplementedError

class DynamicMethodWrapper(AbstractMethodWrapper):
    
    def __init__(self, name, res, args):
        self.dynmeth = Utils.CreateDynamicMethod(name, res, args)

    def get_il_generator(self): 
        return self.dynmeth.GetILGenerator()

    def create_delegate(self, delegatetype, consts):
        return self.dynmeth.CreateDelegate(delegatetype, consts)


# the assemblyData singleton contains the informations about the
# assembly we are currently writing to
class AssemblyData:
    assembly = None
    name = None
    methcount = 0

    def is_enabled(self):
        if self.name is None:
            name = os.environ.get('PYPYJITLOG')
            if name is None:
                name = ''
            self.name = name
        return bool(self.name)

    def create(self):
        assert self.is_enabled()
        if self.assembly is None:
            name = self.name
            self.auto_save_assembly = AutoSaveAssembly.Create(name)
            self.assembly = self.auto_save_assembly.GetAssemblyBuilder()
            self.module = self.assembly.DefineDynamicModule(name)
        
assemblyData = AssemblyData()


class AssemblyMethodWrapper(AbstractMethodWrapper):
    
    def __init__(self, name, res, args):
        module = assemblyData.module
        name = '%s_%d' % (name, assemblyData.methcount)
        #self.name = name
        assemblyData.methcount += 1
        self.typeBuilder = AutoSaveAssembly.DefineType(module, name)
        self.meth = AutoSaveAssembly.DefineMethod(self.typeBuilder,
                                                  "invoke", res, args)


    def get_il_generator(self):
        return self.meth.GetILGenerator()

    def create_delegate(self, delegatetype, consts):
        t = self.typeBuilder.CreateType()
        methinfo = t.GetMethod("invoke")
##         if self.name == 'Loop1(r0)_1':
##             assemblyData.auto_save_assembly.Save()
        return System.Delegate.CreateDelegate(delegatetype,
                                              consts,
                                              methinfo)

def get_method_wrapper(name, res, args):
    if assemblyData.is_enabled():
        assemblyData.create()
        return AssemblyMethodWrapper(name, res, args)
    else:
        return DynamicMethodWrapper(name, res, args)

