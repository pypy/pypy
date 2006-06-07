from pypy.translator.cli import oopspec
from pypy.rpython.ootypesystem import ootype
from pypy.translator.oosupport.metavm import Generator, InstructionList, MicroInstruction

class _Call(MicroInstruction):
    def render(self, generator, op):
        graph = op.args[0].value.graph
        method_name = oopspec.get_method_name(graph, op)
        if method_name is None:
            self._render_function(generator, graph, op.args)
        else:
            self._render_method(generator, method_name, op.args[1:])

    def _render_function(self, generator, graph, args):
        #func_sig = generator.function_signature(graph)
        for func_arg in args[1:]: # push parameters
            generator.load(func_arg)
        generator.call_graph(graph)

    def _render_method(self, generator, method_name, args):
        this = args[0]
        for arg in args: # push parametes
            generator.load(arg)
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

class _CastTo(MicroInstruction):
    def render(self, generator, op):
        generator.load(op.args[0])
        generator.isinstance(op.args[1].value._name)

Call = _Call()
CallMethod = _CallMethod()
IndirectCall = _IndirectCall()
RuntimeNew = _RuntimeNew()
GetField = _GetField()
CastTo = _CastTo()
