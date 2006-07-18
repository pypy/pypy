from pypy.translator.cli import oopspec
from pypy.rpython.ootypesystem import ootype
from pypy.translator.oosupport.metavm import Generator, InstructionList, MicroInstruction
from pypy.translator.cli.comparer import EqualityComparer

STRING_HELPER_CLASS = '[pypylib]pypy.runtime.String'

class _Call(MicroInstruction):
    def render(self, generator, op):
        graph = op.args[0].value.graph
        method_name = oopspec.get_method_name(graph, op)
        if method_name is None:
            self._render_function(generator, graph, op.args)
        else:
            self._render_method(generator, method_name, op.args[1:])

    def _render_function(self, generator, graph, args):
        primitive = getattr(graph.func, 'suggested_primitive', False)
        for func_arg in args[1:]: # push parameters
            generator.load(func_arg)

        if primitive:
            func_name = '[pypylib]pypy.builtin.Builtin::%s' % graph.func.func_name
            generator.call_graph(graph, func_name)
        else:
            generator.call_graph(graph)

    def _render_method(self, generator, method_name, args):
        this = args[0]
        for arg in args: # push parametes
            generator.load(arg)

        # XXX: very hackish, need refactoring
        if this.concretetype is ootype.String:
            # special case for string: don't use methods, but plain functions
            METH = this.concretetype._METHODS[method_name]
            cts = generator.cts
            ret_type = cts.lltype_to_cts(METH.RESULT)
            arg_types = [cts.lltype_to_cts(arg) for arg in METH.ARGS if arg is not ootype.Void]
            arg_types.insert(0, cts.lltype_to_cts(ootype.String))
            arg_list = ', '.join(arg_types)
            signature = '%s %s::%s(%s)' % (ret_type, STRING_HELPER_CLASS, method_name, arg_list)
            generator.call_signature(signature)
        else:
            generator.call_method(this.concretetype, method_name)


class _CallMethod(_Call):
    def render(self, generator, op):
        method = op.args[0]
        self._render_method(generator, method.value, op.args[1:])


class _IndirectCall(_Call):
    def render(self, generator, op):
        # discard the last argument because it's used only for analysis
        self._render_method(generator, 'Invoke', op.args[:-1])

class _RuntimeNew(MicroInstruction):
    def render(self, generator, op):
        generator.load(op.args[0])
        generator.call_signature('object [pypylib]pypy.runtime.Utils::RuntimeNew(class [mscorlib]System.Type)')
        generator.cast_to(op.result.concretetype)

class _GetField(MicroInstruction):
    def render(self, generator, op):
        if op.result.concretetype is ootype.Void:
            return
        this, field = op.args
        generator.load(this)
        generator.get_field(this.concretetype, field.value)

class _SetField(MicroInstruction):
    def render(self, generator, op):
        this, field, value = op.args
        if value.concretetype is ootype.Void:
            return
        generator.load(this)
        generator.load(value)
        generator.set_field(this.concretetype, field.value)


class _CastTo(MicroInstruction):
    def render(self, generator, op):
        generator.load(op.args[0])
        INSTANCE = op.args[1].value
        class_name = generator.db.pending_class(INSTANCE)
        generator.isinstance(class_name)

class _OOString(MicroInstruction):
    def render(self, generator, op):
        ARGTYPE = op.args[0].concretetype
        if isinstance(ARGTYPE, ootype.Instance):
            argtype = 'object'
        else:
            argtype = generator.cts.lltype_to_cts(ARGTYPE)
        generator.load(op.args[0])
        generator.load(op.args[1])
        generator.call_signature('string [pypylib]pypy.runtime.Utils::OOString(%s, int32)' % argtype)

class _DownCast(MicroInstruction):
    def render(self, generator, op):
        RESULTTYPE = op.result.concretetype
        resulttype = generator.cts.lltype_to_cts(RESULTTYPE)
        generator.load(op.args[0])
        generator.ilasm.opcode('castclass', resulttype)

class _NewCustomDict(MicroInstruction):
    def render(self, generator, op):
        DICT = op.args[0].value
        comparer = EqualityComparer(generator.db, DICT._KEYTYPE,
                                    (op.args[1], op.args[2], op.args[3]),
                                    (op.args[4], op.args[5], op.args[6]))
        generator.db.pending_node(comparer)
        dict_type = generator.cts.lltype_to_cts(DICT)

        generator.ilasm.new(comparer.get_ctor())
        generator.ilasm.new('instance void %s::.ctor(class'
                            '[mscorlib]System.Collections.Generic.IEqualityComparer`1<!0>)'
                            % dict_type)

class _CastWeakAdrToPtr(MicroInstruction):
    def render(self, generator, op):
        RESULTTYPE = op.result.concretetype
        resulttype = generator.cts.lltype_to_cts(RESULTTYPE)
        generator.load(op.args[0])
        generator.ilasm.call_method('object class [mscorlib]System.WeakReference::get_Target()', True)
        generator.ilasm.opcode('castclass', resulttype)

Call = _Call()
CallMethod = _CallMethod()
IndirectCall = _IndirectCall()
RuntimeNew = _RuntimeNew()
GetField = _GetField()
SetField = _SetField()
CastTo = _CastTo()
OOString = _OOString()
DownCast = _DownCast()
NewCustomDict = _NewCustomDict()
CastWeakAdrToPtr = _CastWeakAdrToPtr()
