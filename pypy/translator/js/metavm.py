""" Opcode meaning objects, descendants of MicroInstruction
"""

#from pypy.translator.js.jsbuiltin import Builtins
from pypy.translator.oosupport.metavm import PushArg, PushAllArgs, StoreResult,\
    InstructionList, New, GetField, MicroInstruction

from pypy.translator.js.log import log
from pypy.rpython.ootypesystem import ootype
from types import FunctionType
from pypy.objspace.flow.model import Constant

class NewBuiltin(MicroInstruction):
    def __init__(self, arg):
        self.arg = arg
    
    def render(self, generator, op):
        generator.ilasm.new(self.arg)

class _ListSetitem(MicroInstruction):
    def render(self, generator, op):
        generator.load(op.args[1])
        generator.load(op.args[3])
        generator.load(op.args[2])
        generator.ilasm.list_setitem()
ListSetitem = _ListSetitem()

class _ListGetitem(MicroInstruction):
    def render(self, generator, op):
        generator.load(op.args[1])
        generator.load(op.args[2])
        generator.ilasm.list_getitem()
ListGetitem = _ListGetitem()

class _ListContains(MicroInstruction):
    def render(self, generator, op):
        generator.load(op.args[1])
        generator.load(op.args[2])
        generator.ilasm.list_getitem()
        generator.ilasm.load_void()
        generator.emit('!=')
ListContains = _ListContains()

class _Call(MicroInstruction):
    def render(self, generator, op):
        graph = op.args[0].value.graph
        self._render_function(generator, graph, op.args)

    def _render_builtin(self, generator, builtin, args):
        for func_arg in args[1:]: # push parameters
            generator.load(func_arg)
        generator.call_external(builtin, args[1:])

    def _render_builtin_prepared_args(self, generator, builtin, args):
        for func_arg in args:
            generator.load_str(func_arg)
        generator.call_external(builtin, args)
    
    def _render_builtin_method(self, generator, builtin, args):
        for func_arg in args:
            generator.load_special(func_arg)
        generator.call_external_method(builtin, len(args)-1)

    def _render_function(self, generator, graph, args):
        for func_arg in args[1:]: # push parameters
            if func_arg.concretetype is not ootype.Void:
                generator.load(func_arg)
        generator.call_graph(graph)
    
    def _render_method(self, generator, method_name, args):
        this = args[0]
        for arg in args: # push parametes
            generator.load(arg)
        generator.call_method(this.concretetype, method_name)

Call = _Call()

class CallBuiltin(_Call):
    def __init__(self, builtin):
        self.builtin = builtin
    
    def render(self, generator, op):
        self._render_builtin(generator, self.builtin, op.args)

class CallBuiltinMethod(_Call):
    def __init__(self, builtin, slice=None, additional_args=[]):
        self.builtin = builtin
        self.slice = slice
        self.additional_args = additional_args

    def render(self, generator, op):
        if self.slice is not None:
            args = op.args[self.slice]
        else:
            args = op.args
        args += self.additional_args
        self._render_builtin_method(generator, self.builtin, args)

class _SameAs(MicroInstruction):
    def render(self, generator, op):
        generator.change_name(op.result, op.args[0])

class _CastFun(MicroInstruction):
    def __init__(self, name, num):
        self.name = name
        self.num = num

    def render(self, generator, op):
        log("Args: %r"%op.args)
        generator.cast_function(self.name, self.num)

class _Prefix(MicroInstruction):
    def __init__(self, st):
        self.st = st
    
    def render(self, generator, op):
        generator.prefix_op(self.st)

class _NotImplemented(MicroInstruction):
    def __init__(self, reason):
        self.reason = reason
    
    def render(self, generator, op):
        raise NotImplementedError(self.reason)
        
class _CastMethod(MicroInstruction):
    def __init__(self, method_name, num=0):
        self.method_name = method_name
        self.num = num

    def render(self, generator, op):
        generator.call_external_method(self.method_name, self.num)

class _LoadConst(MicroInstruction):
    def __init__(self, value):
        self.value = value

    def render(self, generator, op):
        generator.load(Constant(self.value, ootype.typeOf(self.value)))
    
class _GetBuiltinField(MicroInstruction):
    def render(self, generator, op):
        this = op.args[0]
        field = op.args[1].value[1:]
        generator.load(this)
        generator.get_field(None, field)

class _GetPredefinedField(MicroInstruction):
    def __init__(self, field, num=1):
        self.field = field
        self.num = num

    def render(self, generator, op):
        if op.result.concretetype is ootype.Void:
            return
        this = op.args[self.num]
        generator.load(this)
        generator.get_field(None, self.field)

GetBuiltinField = _GetBuiltinField()

class _SetBuiltinField(MicroInstruction):
    def render(self, generator, op):
        this = op.args[0]
        field = op.args[1].value
        if not field.startswith('o'):
            generator.load_void()
        else:
            value = op.args[2]
            field_name = field[1:]
            self.run_it(generator, this, field_name, value)
    
    def run_it(self, generator, this, field_name, value):
        generator.load(this)
        generator.load_special(value)
        generator.set_field(None, field_name)

class _SetPredefinedField(_SetBuiltinField):
    def __init__(self, field):
        self.field = field

    def render(self, generator, op):
        value = op.args[2]
        this = op.args[1]
        self.run_it(generator, this, self.field, value)
    
class _SetExternalField(_SetBuiltinField):
    def render(self, generator, op):
        self.run_it(generator, op.args[0], op.args[1].value, op.args[2])

SetBuiltinField = _SetBuiltinField()
SetExternalField = _SetExternalField()

class _CallMethod(_Call):
    def render(self, generator, op):
        method = op.args[0]
        self._render_method(generator, method.value, op.args[1:])

class _CallBuiltinObject(_Call):
    def render(self, generator, op):
        this = op.args[1].concretetype
        method = op.args[0]
        method_name = this._methods[method.value]._name[1:]
        generator.load(op.args[1])
        self._render_builtin_method(generator, method_name, op.args[1:])

class _CallExternalObject(_Call):
    def render(self, generator, op):
        this = op.args[1].concretetype
        method = op.args[0]
        method_name = method.value
        #generator.load(op.args[1])
        self._render_builtin_method(generator, method_name, op.args[1:])

CallBuiltinObject = _CallBuiltinObject()
CallExternalObject = _CallExternalObject()

class _IsInstance(MicroInstruction):
    def render(self, generator, op):
        # FIXME: just temporary hack
        generator.load(op.args[0])
        generator.ilasm.load_const(op.args[1].value._name.replace('.', '_'))#[-1])
        generator.cast_function("isinstanceof", 2)

class _IndirectCall(MicroInstruction):
    def render(self, generator, op):
        for func_arg in op.args[1:]: # push parameters
            generator.load(func_arg)
        generator.call_external(op.args[0].name, op.args[1:])

class _SetTimeout(MicroInstruction):
    # FIXME: Dirty hack for javascript callback stuff
    def render(self, generator, op):
        val = op.args[1].value
        assert(isinstance(val, ootype._static_meth))
        #if isinstance(val, ootype.StaticMethod):
        real_name = val._name
        generator.db.pending_function(val.graph)
            #generator.db.pending_function(val.graph)
        #else:
        #    concrete = val.concretize()
        #    real_name = concrete.value._name
        #    generator.db.pending_function(concrete.value.graph)
        generator.load_str("'%s()'" % real_name)
        generator.load(op.args[2])
        generator.call_external('setTimeout',[0]*2)

class _DiscardStack(MicroInstruction):
    def render(self, generator, op):
        generator.clean_stack()

class SetOnEvent(MicroInstruction):
    def __init__(self, field):
        self.field = field
    
    # FIXME: Dirty hack for javascript callback stuff
    def render(self, generator, op):
        val = op.args[1].value
        val = val.concretize().value
        assert(isinstance(val, ootype._static_meth))
        real_name = val._name
        generator.db.pending_function(val.graph)
        generator.load_str("document")
        generator.load_str(real_name)
        generator.set_field(None, self.field)

class _CheckLength(MicroInstruction):
    def render(self, generator, op):
        assert not generator.ilasm.right_hand

class _ListRemove(MicroInstruction):
    def render(self, generator, op):
        generator.list_getitem(op.args[1], op.args[2])
        generator.call_external('delete', [0])

ListRemove = _ListRemove()
CheckLength = _CheckLength()
SetTimeout = _SetTimeout()
IndirectCall = _IndirectCall()
IsInstance = _IsInstance()
CallMethod = _CallMethod()
CopyName = [PushAllArgs, _SameAs ()]
CastString = _CastFun("convertToString", 1)
SameAs = CopyName
DiscardStack = _DiscardStack()

def fix_opcodes(opcodes):
    for key, value in opcodes.iteritems():
        if type(value) is str:
            value = InstructionList([PushAllArgs, value, StoreResult, CheckLength])
        elif value == []:
            value = InstructionList([CheckLength])
        elif value is not None:
            if StoreResult not in value:
                value.append(StoreResult)
            if CheckLength not in value:
                value.append(CheckLength)
            value = InstructionList(value)

        opcodes[key] = value
