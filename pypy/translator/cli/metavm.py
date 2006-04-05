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
        func_sig = generator.function_signature(op.args[0].value.graph)

        # push parameters
        for func_arg in op.args[1:]:
            generator.load(func_arg)

        generator.call(func_sig)

class _New(MicroInstruction):
    def render(self, generator, op):
        generator.new(op.args[0].value)

class _SetField(MicroInstruction):
    def render(self, generator, op):
        this, field, value = op.args
        if field.value == 'meta':
            return # TODO
        
        generator.load(this)
        generator.load(value)
        generator.set_field(this.concretetype, field.value)

class _GetField(MicroInstruction):
    def render(self, generator, op):
        this, field = op.args
        generator.load(this)
        generator.get_field(this.concretetype, field.value)

class _CallMethod(MicroInstruction):
    def render(self, generator, op):
        method = op.args[0]
        this = op.args[1]

        # push parameters
        for func_arg in op.args[1:]:
            generator.load(func_arg)

        generator.call_method(this.concretetype, method.value)


PushAllArgs = _PushAllArgs()
StoreResult = _StoreResult()
Call = _Call()
New = _New()
SetField = _SetField()
GetField = _GetField()
CallMethod = _CallMethod()
