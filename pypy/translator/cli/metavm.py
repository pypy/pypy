from pypy.translator.cli import oopspec

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


class MicroInstruction(object):
    def render(self, generator, op):
        pass

    def __str__(self):
        return self.__class__.__name__


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

class _New(MicroInstruction):
    def render(self, generator, op):
        generator.new(op.args[0].value)

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

class _RuntimeNew(MicroInstruction):
    def render(self, generator, op):
        generator.load(op.args[0])
        generator.call_signature('object [pypylib]pypy.runtime.Utils::RuntimeNew(class [mscorlib]System.Type)')
        generator.cast_to(op.result.concretetype)


PushAllArgs = _PushAllArgs()
StoreResult = _StoreResult()
Call = _Call()
New = _New()
SetField = _SetField()
GetField = _GetField()
CallMethod = _CallMethod()
RuntimeNew = _RuntimeNew()
