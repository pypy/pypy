
""" Opcode meaning objects, descendants of MicroInstruction
"""

#from pypy.translator.js2.jsbuiltin import Builtins
from pypy.translator.cli.metavm import PushArg, PushAllArgs, StoreResult,\
    InstructionList, New, SetField, GetField, RuntimeNew, MicroInstruction

from pypy.translator.js2.log import log
from pypy.rpython.ootypesystem import ootype

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

class _Call(MicroInstruction):
    def render(self, generator, op):
        graph = op.args[0].value.graph
        self._render_function(generator, graph, op.args)

    def _render_builtin(self, generator, builtin, args):
        for func_arg in args[1:]: # push parameters
            generator.load(func_arg)
        generator.call_external(builtin, args[1:])
    
    def _render_builtin_method(self, generator, builtin, args, is_property):
        if not is_property:
            for func_arg in args:
                generator.load(func_arg)
            generator.call_external_method(builtin, len(args)-1)
        else:
            generator.load(args[0])
            generator.get_field(None, builtin)

    def _render_function(self, generator, graph, args):
        for func_arg in args[1:]: # push parameters
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

class _Builtins(object):
    def __init__(self):
        list_resize = lambda g,op: SetBuiltinField.run_it(g, op.args[1], 'length', op.args[2])
        
        self.builtin_map = {
            'll_js_jseval' : CallBuiltin('eval'),
            'll_newlist' : lambda g,op: g.ilasm.load_const("[]"),
            'll_alloc_and_set' : CallBuiltin('alloc_and_set'),
        }
        self.builtin_obj_map = {
            ootype.String.__class__: {
                'll_strconcat' : InstructionList([PushAllArgs, '+']),
                'll_strlen' : lambda g,op: GetBuiltinField.run_it(g, op.args[1], 'length'),
                'll_stritem_nonneg' : ListGetitem,
                'll_streq' : InstructionList([PushAllArgs, '==']),
                'll_strcmp' : CallBuiltin('strcmp'),
                'll_startswith' : CallBuiltin('startswith'),
                'll_endswith' : CallBuiltin('endswith'),
            },
            ootype.List: {
                'll_setitem_fast' : ListSetitem,
                'll_getitem_fast' : ListGetitem,
                '_ll_resize' : list_resize,
                '_ll_resize_ge' : list_resize,
                '_ll_resize_le' : list_resize,
                'll_length' : lambda g,op: GetBuiltinField.run_it(g, op.args[1], 'length'),
            }
        }
        
Builtins = _Builtins()

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
    
class _GetBuiltinField(MicroInstruction):
    def render(self, generator, op):
        this = op.args[0]
        field = op.args[1]
        field_name = this.value.methods[field].name[1:]
        self.run_it(generator, this, field_name)
    
    def run_it(self, generator, this, field_name):
        generator.load(this)
        generator.get_field(None, field_name)

GetBuiltinField = _GetBuiltinField()

class _SetBuiltinField(MicroInstruction):
    def render(self, generator, op):
        this = op.args[0]
        field = op.args[1]
        value = op.args[2]
        field_name = this.value.methods[field].name[1:]
        self.run_it(generator, this, field_name, value)
    
    def run_it(self, generator, this, field_name, value):
        generator.load(this)
        generator.load(value)
        generator.set_field(None, field_name)

SetBuiltinField = _SetBuiltinField()

class _CallMethod(_Call):
    def render(self, generator, op):
        method = op.args[0]
        self._render_method(generator, method.value, op.args[1:])

class _IsInstance(MicroInstruction):
    def render(self, generator, op):
        # FIXME: just temporary hack
        generator.load(op.args[0])
        generator.ilasm.load_const(op.args[1].value._name.replace('.', '_'))#[-1])
        generator.cast_function("isinstanceof", 2)

# There are three distinct possibilities where we need to map call differently:
# 1. Object is marked with rpython_hints as a builtin, so every attribut access
#    and function call goes as builtin
# 2. Function called is a builtin, so it might be mapped to attribute access, builtin function call
#    or even method call
# 3. Object on which method is called is primitive object and method is mapped to some
#    method/function/attribute access
class _GeneralDispatcher(MicroInstruction):
    def render(self, generator, op):
        raise NotImplementedError("pure virtual class")
    
    def check_builtin(self, this):
        if not isinstance(this, ootype.Instance):
            return False
        return this._hints.get('_suggested_external')

class _MethodDispatcher(_GeneralDispatcher):
    def render(self, generator, op):
        method = op.args[0].value
        this = op.args[1].concretetype
        if self.check_builtin(this):
            return CallBuiltinObject.render(generator, op)
        try:
            Builtins.builtin_obj_map[this.__class__][method](generator, op)
            log("%r.%r declared builtin" % (this, method))
        except KeyError:
            log("%r.%r declared normal" % (this, method))
            CallMethod.render(generator, op)

class _CallDispatcher(_GeneralDispatcher):
    def render(self, generator, op):
        func = op.args[0]
        if getattr(func.value._callable, 'suggested_primitive', False):
            func_name = func.value._name.split("__")[0]
            log("Function name: %s suggested primitive" % func_name)
            if Builtins.builtin_map.has_key(func_name):
                return Builtins.builtin_map[func_name](generator, op)
        else:
            return Call.render(generator, op)
    
class _GetFieldDispatcher(_GeneralDispatcher):
    def render(self, generator, op):
        if self.check_builtin(op.args[0].concretetype):
            return GetBuiltinField.render(generator, op)
        else:
            return GetField.render(generator, op)
    
class _SetFieldDispatcher(_GeneralDispatcher):
    def render(self, generator, op):
        if self.check_builtin(op.args[0].concretetype):
            return SetBuiltinField.render(generator, op)
        else:
            return SetField.render(generator, op)

MethodDispatcher = _MethodDispatcher()
CallDispatcher = _CallDispatcher()
GetFieldDispatcher = _GetFieldDispatcher()
SetFieldDispatcher = _SetFieldDispatcher()
IsInstance = _IsInstance()
CallMethod = _CallMethod()
CopyName = [PushAllArgs, _SameAs ()]
CastString = _CastString()
SameAs = CopyName
