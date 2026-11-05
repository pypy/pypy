"""
The instructions that the flow space interprets.

A decoder translates a host code object into a list of these instructions
(see bytecode.FlowCode). Operands are fully resolved and jump targets are
positions in the instruction list. Each instruction implements eval(ctx),
which runs it on a FlowContext and returns the position of the next
instruction, or None to continue with the following one.
"""
from rpython.flowspace.model import Constant, Variable, const
from rpython.flowspace.operation import op
from rpython.flowspace.flowcontext import FlowingError


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


class Unsupported(Instr):
    def __init__(self, message):
        self.message = message

    def eval(self, ctx):
        raise FlowingError(self.message)


# ____________________________________________________________
# Variables and names

class LoadFast(Instr):
    def __init__(self, index):
        self.index = index

    def eval(self, ctx):
        w_value = ctx.locals_w[self.index]
        if w_value is None:
            raise FlowingError("Local variable referenced before assignment")
        ctx.pushvalue(w_value)


class StoreFast(Instr):
    def __init__(self, index):
        self.index = index

    def eval(self, ctx):
        w_newvalue = ctx.popvalue()
        assert w_newvalue is not None
        ctx.locals_w = ctx.locals_w[:]
        ctx.locals_w[self.index] = w_newvalue
        if isinstance(w_newvalue, Variable):
            w_newvalue.rename(ctx.code.varnames[self.index])


class DeleteFast(Instr):
    def __init__(self, index):
        self.index = index

    def eval(self, ctx):
        if ctx.locals_w[self.index] is None:
            varname = ctx.code.varnames[self.index]
            message = "local variable '%s' referenced before assignment"
            raise UnboundLocalError(message, varname)
        ctx.locals_w = ctx.locals_w[:]
        ctx.locals_w[self.index] = None


class LoadConst(Instr):
    def __init__(self, value):
        self.value = value

    def eval(self, ctx):
        ctx.pushvalue(const(self.value))


class LoadGlobal(Instr):
    def __init__(self, name):
        self.name = name

    def eval(self, ctx):
        ctx.pushvalue(ctx.find_global(ctx.w_globals, self.name))


class LoadDeref(Instr):
    def __init__(self, index):
        self.index = index

    def eval(self, ctx):
        cell = ctx.closure[self.index]
        try:
            content = cell.cell_contents
        except ValueError:
            name = ctx.code.freevars[self.index]
            raise FlowingError("Undefined closure variable '%s'" % name)
        ctx.pushvalue(const(content))


class LoadAttr(Instr):
    def __init__(self, name):
        self.name = name

    def eval(self, ctx):
        w_obj = ctx.popvalue()
        w_value = op.getattr(w_obj, Constant(self.name)).eval(ctx)
        ctx.pushvalue(w_value)


class StoreAttr(Instr):
    def __init__(self, name):
        self.name = name

    def eval(self, ctx):
        w_obj = ctx.popvalue()
        w_newvalue = ctx.popvalue()
        op.setattr(w_obj, Constant(self.name), w_newvalue).eval(ctx)


class ImportName(Instr):
    def __init__(self, name):
        self.name = name

    def eval(self, ctx):
        glob = ctx.w_globals.value
        fromlist = ctx.popvalue().value
        level = ctx.popvalue().value
        w_obj = ctx.import_name(self.name, glob, None, fromlist, level)
        ctx.pushvalue(w_obj)


class ImportFrom(Instr):
    def __init__(self, name):
        self.name = name

    def eval(self, ctx):
        w_module = ctx.peekvalue()
        ctx.pushvalue(ctx.import_from(w_module, Constant(self.name)))
