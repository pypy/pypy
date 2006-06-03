
""" opcode definitions
"""

from pypy.translator.cli.metavm import PushArg, PushAllArgs, StoreResult,\
     InstructionList, New, SetField, GetField, RuntimeNew, MicroInstruction

DoNothing = [PushAllArgs]

from pypy.translator.js2._builtin import Builtins
from pypy.translator.js2.log import log

##class _GetField(MicroInstruction):
##    def render(self, generator, op):
##        this, field = op.args
##        generator.load(this)
##        generator.get_field(this.concretetype, field.value)

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
        
class _New(MicroInstruction):
    def render(self, generator, op):
        generator.new(op.args[0].value)

class _CastString(MicroInstruction):
    def render(self, generator, op):
        this = op.args[0]
        generator.load(this)
        generator.call_external_method("toString", 0)

class _Call(MicroInstruction):
    def render(self, generator, op):
        graph = op.args[0].value.graph
        #method_name = oopspec.get_method_name(graph, op)
        #if method_name is None:
        bt = Builtins.map_builtin_function(op.args[0], self, op.args, generator)
        if bt:
            builtin, is_property = bt
            self._render_builtin(generator, builtin, op.args, is_property)
            log("Suggested builtin %r %r"%(bt, is_property))
        if bt is None:
            self._render_function(generator, graph, op.args)
        #else:
        #    self._render_method(generator, method_name, op.args[1:])

    def _render_builtin(self, generator, builtin, args, is_property):
        if not is_property:
            for func_arg in args[1:]: # push parameters
                generator.load(func_arg)
            generator.call_external(builtin, args[1:])
        else:
            generator.load_str(builtin)
    
    def _render_builtin_method(self, generator, builtin, args, is_property):
        if not is_property:
            for func_arg in args:
                generator.load(func_arg)
            generator.call_external_method(builtin, len(args)-1)
        else:
            generator.load(args[0])
            generator.get_field(None, builtin)

    def _render_function(self, generator, graph, args):
        #func_sig = generator.function_signature(graph)
        for func_arg in args[1:]: # push parameters
            generator.load(func_arg)
        generator.call_graph(graph)
    
    # Various low level function-to-operator mappings
    
    def list_ll_setitem(self, base_obj, args, generator):
        generator.list_setitem(base_obj, args[1], args[2])
    
    def list_ll_getitem(self, base_obj, args, generator):
        generator.list_getitem(base_obj, args[1])
    
    def list_ll_resize(self, base_obj, args, generator):
        generator.list_resize(base_obj, args[1])
    
    def do_nothing(self, base_obj, args, generator):
        generator.load_void()
    
    def equal(self, base_obj, args, generator):
        generator.load(args[1])
        generator.load(args[2])
        generator.emit("==")

    def _render_method(self, generator, method_name, args):
        this = args[0]
        bt = Builtins.map_builtin_method(this, method_name, args, self, generator)
        if bt:
            function,is_property = bt
            self._render_builtin_method(generator, function, args, is_property)
        if bt is None:
            for arg in args: # push parametes
                generator.load(arg)
            generator.call_method(this.concretetype, method_name)

class _CallMethod(_Call):
    def render(self, generator, op):
        method = op.args[0]
        self._render_method(generator, method.value, op.args[1:])

class _IsInstance(MicroInstruction):
    def render(self, generator, op):
        # FIXME: just temporary hack
        generator.load(op.args[0])
        generator.ilasm.load_const(op.args[1].value._name.split('.')[-1])
        generator.cast_function("isinstanceof", 2)

IsInstance = _IsInstance()
Call = _Call()
CallMethod = _CallMethod()
CopyName = [PushAllArgs, _SameAs ()]
CastString = _CastString()
SameAs = CopyName

opcodes = {'int_mul': '*',
    'int_add': '+',
    'int_sub': '-',
    'int_floordiv': '/',
    'int_mod': '%',
    'int_and': '&',
    'int_or': '|',
    'int_xor': '^',
    'int_lshift': '<<',
    'int_rshift': '>>',
    'int_lt': '<',
    'int_le': '<=',
    'int_eq': '==',
    'int_ne': '!=',
    'int_ge': '>=',
    'int_gt': '>',

    'uint_mul': '*',
    'uint_add': '+',
    'uint_sub': '-',
    'uint_floordiv': '/',
    'uint_mod': '%',
    'uint_and': '&',
    'uint_or': '|',
    'uint_xor': '^',
    'uint_lshift': '<<',
    'uint_rshift': '>>',
    'uint_lt': '<',
    'uint_le': '<=',
    'uint_eq': '==',
    'uint_ne': '!=',
    'uint_ge': '>=',
    'uint_gt': '>',

    'unichar_lt': '<',
    'unichar_le': '<=',
    'unichar_eq': '==',
    'unichar_ne': '!=',
    'unichar_ge': '>=',
    'unichar_gt': '>',
    
    'char_lt': '<',
    'char_le': '<=',
    'char_eq': '==',
    'char_ne': '!=',
    'char_ge': '>=',
    'char_gt': '>',

    'float_mul': '*',
    'float_add': '+',
    'float_sub': '-',
    'float_truediv': '/',
    'float_mod': '%',
    'float_lt': '<',
    'float_le': '<=',
    'float_eq': '==',
    'float_ne': '!=',
    'float_ge': '>=',
    'float_gt': '>',

    'ptr_eq': '==',
    'ptr_ne': '!=',

    'bool_not': [PushAllArgs,_Prefix('!')],
    'int_neg': [PushAllArgs,_Prefix('-')],
    'int_invert': [PushAllArgs,_Prefix('~')],
    'float_neg': [PushAllArgs,_Prefix('-')],
        
    'float_pow': [PushAllArgs,_CastFun('Math.pow',2)],
    'int_abs': [PushAllArgs,_CastFun('Math.abs',1)],
    'float_abs': [PushAllArgs,_CastFun('Math.abs',1)],

    'int_is_true': [PushAllArgs,_Prefix('!!')],
    'uint_is_true': [PushAllArgs,_Prefix('!!')],
    'float_is_true': [PushAllArgs,_Prefix('!!')],
    
    'direct_call' : [Call],
    'indirect_call' : [_NotImplemented("Indirect call not implemented")],
    'same_as' : SameAs,
    'new' : [New],
    'instanceof' : [IsInstance],
    
    # objects
    
    'oosetfield' : [SetField],
    'oogetfield' : [GetField],
    'oosend'     : [CallMethod],
    #'ooupcast'   : [_NotImplemented("Inheritance not implemented (ooupcast)")],
    #'oodowncast' : [_NotImplemented("Inheritance not implemented (oodowncast)")],
    'ooupcast'   : DoNothing,
    'oodowncast' : DoNothing,        
    'oononnull'  : [PushAllArgs,_Prefix('!!')],
    'oostring'   : [CastString],
    'oois'       : '==', # FIXME: JS does not have real equal
    # when casting from bool we want that every truth value is casted
    # to 1: we can't simply DoNothing, because the CLI stack could
    # contains a truth value not equal to 1, so we should use the !=0
    # trick.
    'cast_bool_to_int':         CopyName,
    'cast_bool_to_uint':        CopyName,
    'cast_bool_to_float':       CopyName,
    'cast_char_to_int':         CopyName,
    'cast_unichar_to_int':      CopyName,
    'cast_int_to_char':         CopyName,
    'cast_int_to_unichar':      CopyName,
    'cast_int_to_uint':         CopyName,
    'cast_int_to_float':        CopyName,
    'cast_int_to_longlong':     CopyName,
    'cast_uint_to_int':         CopyName,
    'cast_uint_to_float':       CopyName,
    'cast_float_to_int':        [PushAllArgs,_CastFun("Math.floor",1)],
    'cast_float_to_uint':       [PushAllArgs,_CastFun("Math.floor",1)],
    'truncate_longlong_to_int': CopyName,
}

for key, value in opcodes.iteritems():
    if type(value) is str:
        value = InstructionList([PushAllArgs, value, StoreResult])
    elif value is not None:
        if StoreResult not in value:
            value.append(StoreResult)
        value = InstructionList(value)

    opcodes[key] = value
