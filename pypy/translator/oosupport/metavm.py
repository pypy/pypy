
"""
Varius microopcodes for different ootypesystem based backends

These microopcodes are used to translate from the ootype operations to
the operations of a particular backend.  For an example, see
cli/opcodes.py which maps from ootype opcodes to sets of metavm
instructions.

See the MicroInstruction class for discussion on the methods of a
micro-op.
"""

from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.bltregistry import ExternalType

class Generator(object):

    def emit(self, instr, *args):
        """
        Invoked by InstructionList.render() when we encounter a
        non-MicroInstruction in the list of instructions.  This is
        typically used to encode small single operands as strings.
        """
        pass

    def load(self, v):
        """
        Loads an item 'v' onto the stack
        
        Stack: ... -> v, ...
        """
        pass

    def store(self, v):
        """
        Stores an item from the stack into 'v'
        
        Stack: value, ... -> ...
        """
        pass

    def set_field(self, concretetype, value):
        """
        Stores a value into a field.
        
        'concretetype' should be the type of the class that has the field
        'value' is the value of field.value (where field comes from the op)
        
        Stack: value, item, ... -> ...
        """
        pass

    def get_field(self, concretetype, value):
        """
        Gets a value from a specified field.

        'concretetype' should be the type of the class that has the field
        'value' is the value of field.value (where field comes from the op)

        Stack: item, ... -> ...
        """
        pass

    def downcast(self, type):
        """
        Casts the object on the top of the stack to be of the specified
        type.  Assumed to raise an exception on failure.
        
        Stack: obj, ... -> obj, ...
        """
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
        """
        Generic method which emits code to perform this microinstruction.
        
        'generator' -> the class which generates actual code emitted
        'op' -> the instruction from the FlowIR
        """
        pass

    def __str__(self):
        return self.__class__.__name__
    
    def __call__(self, *args):
        return self.render(*args)

class _DoNothing(MicroInstruction):
    def render(self, generator, op):
        pass
        
class PushArg(MicroInstruction):
    """ Pushes a given operand onto the stack. """
    def __init__(self, n):
        self.n = n

    def render(self, generator, op):
        generator.load(op.args[self.n])

class _PushAllArgs(MicroInstruction):
    """ Pushes all arguments of the instruction onto the stack in order. """
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
        
        #if value.concretetype is ootype.Void:
        #    return
        generator.load(this)
        generator.load(value)
        generator.set_field(this.concretetype, field.value)

class _GetField(MicroInstruction):
    def render(self, generator, op):
        # OOType produces void values on occassion that can safely be ignored
        # XXX: That's not true
        #if op.result.concretetype is ootype.Void:
        #    return
        this, field = op.args
        generator.load(this)
        generator.get_field(this.concretetype, field.value)

class _DownCast(MicroInstruction):
    """ Push the argument op.args[0] and cast it to the desired type, leaving
    result on top of the stack. """
    def render(self, generator, op):
        RESULTTYPE = op.result.concretetype
        resulttype = generator.cts.lltype_to_cts(RESULTTYPE)
        generator.load(op.args[0])
        generator.downcast(resulttype)

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
DownCast = _DownCast()
DoNothing = _DoNothing()
