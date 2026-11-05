"""
The instructions that the flow space interprets.

A decoder translates a host code object into a list of these instructions
(see bytecode.FlowCode). Operands are fully resolved and jump targets are
positions in the instruction list. Each instruction implements eval(ctx),
which runs it on a FlowContext and returns the position of the next
instruction, or None to continue with the following one.
"""


class Instr(object):
    offset = -1     # offset of the host instruction this was decoded from

    def eval(self, ctx):
        raise NotImplementedError

    def _operands(self):
        return [(k, v) for k, v in sorted(self.__dict__.items())
                if k != 'offset']

    def __eq__(self, other):
        return (type(self) is type(other) and
                self._operands() == other._operands())

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, ', '.join(
            '%s=%r' % item for item in self._operands()))


class JumpInstr(Instr):
    """An instruction with a 'target' position."""
    def __init__(self, target):
        self.target = target


class HostOpcode(Instr):
    """Temporary: a host opcode run by the FlowContext method of the same
    name."""
    def __init__(self, methodname, oparg):
        self.methodname = methodname
        self.oparg = oparg

    def eval(self, ctx):
        return getattr(ctx, self.methodname)(self.oparg)


class HostJumpOpcode(JumpInstr):
    """Temporary: like HostOpcode, for opcodes with a jump target."""
    def __init__(self, methodname, target):
        self.methodname = methodname
        self.target = target

    def eval(self, ctx):
        return getattr(ctx, self.methodname)(self.target)
