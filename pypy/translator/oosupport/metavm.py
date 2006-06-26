
"""
Varius microopcodes for different ootypesystem based backends
"""

from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.bltregistry import ExternalType

class Generator(object):
    def function_signature(self, graph):
        pass

    def emit(self, instr, *args):
        pass

    def call(self, func_name):
        pass

    def load(self, v):
        pass

    def store(self, v):
        pass


class InstructionList(list):
    def render(self, generator, op):
        for instr in self:
            if isinstance(instr, MicroInstruction):
                instr.render(generator, op)
            else:
                generator.emit(instr)
    
    def __call__(self, *args):
        return self.render(*args)


class MicroInstruction(object):
    def render(self, generator, op):
        pass

    def __str__(self):
        return self.__class__.__name__
    
    def __call__(self, *args):
        return self.render(*args)
        
class PushArg(MicroInstruction):
    def __init__(self, n):
        self.n = n

    def render(self, generator, op):
        generator.load(op.args[self.n])

class _PushAllArgs(MicroInstruction):
    def render(self, generator, op):
        for arg in op.args:
            generator.load(arg)

class _StoreResult(MicroInstruction):
    def render(self, generator, op):
        generator.store(op.result)

class _SetField(MicroInstruction):
    def render(self, generator, op):
        this, field, value = op.args
##        if field.value == 'meta':
##            return # TODO
        
        generator.load(this)
        generator.load(value)
        generator.set_field(this.concretetype, field.value)

class _GetField(MicroInstruction):
    def render(self, generator, op):
        this, field = op.args
        generator.load(this)
        generator.get_field(this.concretetype, field.value)


# There are three distinct possibilities where we need to map call differently:
# 1. Object is marked with rpython_hints as a builtin, so every attribut access
#    and function call goes as builtin
# 2. Function called is a builtin, so it might be mapped to attribute access, builtin function call
#    or even method call
# 3. Object on which method is called is primitive object and method is mapped to some
#    method/function/attribute access
class _GeneralDispatcher(MicroInstruction):
    def __init__(self, builtins, class_map):
        self.builtins = builtins
        self.class_map = class_map
    
    def render(self, generator, op):
        raise NotImplementedError("pure virtual class")
    
    def check_builtin(self, this):
        if not isinstance(this, ootype.Instance):
            return False
        return this._hints.get('_suggested_external')
    
    def check_external(self, this):
        if isinstance(this, ExternalType):
            return True
        return False

class _MethodDispatcher(_GeneralDispatcher):
    def render(self, generator, op):
        method = op.args[0].value
        this = op.args[1].concretetype
        if self.check_external(this):
            return self.class_map['CallExternalObject'].render(generator, op)
        if self.check_builtin(this):
            return self.class_map['CallBuiltinObject'].render(generator, op)
        try:
            self.builtins.builtin_obj_map[this.__class__][method](generator, op)
        except KeyError:
            return self.class_map['CallMethod'].render(generator, op)

class _CallDispatcher(_GeneralDispatcher):
    def render(self, generator, op):
        func = op.args[0]
        if getattr(func.value._callable, 'suggested_primitive', False):
            func_name = func.value._name.split("__")[0]
            try:
                return self.builtins.builtin_map[func_name](generator, op)
            except KeyError:
                return self.class_map['CallBuiltin'](func_name)(generator, op)
        return self.class_map['Call'].render(generator, op)
    
class _GetFieldDispatcher(_GeneralDispatcher):
    def render(self, generator, op):
        if self.check_builtin(op.args[0].concretetype):
            return self.class_map['GetBuiltinField'].render(generator, op)
        else:
            return self.class_map['GetField'].render(generator, op)
    
class _SetFieldDispatcher(_GeneralDispatcher):
    def render(self, generator, op):
        if self.check_external(op.args[0].concretetype):
            return self.class_map['SetExternalField'].render(generator, op)
        elif self.check_builtin(op.args[0].concretetype):
            return self.class_map['SetBuiltinField'].render(generator, op)
        else:
            return self.class_map['SetField'].render(generator, op)

class _New(MicroInstruction):
    def render(self, generator, op):
        try:
            op.args[0].value._hints['_suggested_external']
            generator.ilasm.new(op.args[0].value._name.split('.')[-1])
        except (KeyError, AttributeError):
            generator.new(op.args[0].value)

New = _New()

PushAllArgs = _PushAllArgs()
StoreResult = _StoreResult()
SetField = _SetField()
GetField = _GetField()
