class Generator(object):
    def function_name(self, graph):
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
        func_name = generator.function_name(op.args[0].value.graph)

        # push parameters
        for func_arg in op.args[1:]:
            generator.load(func_arg)

        generator.call(func_name)

PushAllArgs = _PushAllArgs()
StoreResult = _StoreResult()
Call = _Call()
