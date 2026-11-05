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

w_None = const(None)


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
# Stack manipulation

class PopTop(Instr):
    def eval(self, ctx):
        ctx.popvalue()


class Copy(Instr):
    """Push a copy of the n-th item from the top (n=1 is the top)."""
    def __init__(self, n):
        self.n = n

    def eval(self, ctx):
        ctx.pushvalue(ctx.peekvalue(self.n - 1))


class Swap(Instr):
    """Swap the top item with the n-th item from the top."""
    def __init__(self, n):
        self.n = n

    def eval(self, ctx):
        w_top = ctx.peekvalue()
        ctx.settopvalue(ctx.peekvalue(self.n - 1))
        ctx.settopvalue(w_top, self.n - 1)


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


# ____________________________________________________________
# Operators

class UnaryOp(Instr):
    def __init__(self, operation):
        self.operation = operation

    def eval(self, ctx):
        w_1 = ctx.popvalue()
        ctx.pushvalue(self.operation(w_1).eval(ctx))


class UnaryNot(Instr):
    def eval(self, ctx):
        w_obj = ctx.popvalue()
        ctx.pushvalue(ctx.not_(w_obj))


class BinaryOp(Instr):
    def __init__(self, operation):
        self.operation = operation

    def eval(self, ctx):
        w_2 = ctx.popvalue()
        w_1 = ctx.popvalue()
        ctx.pushvalue(self.operation(w_1, w_2).eval(ctx))


class Compare(Instr):
    """'kind' names one of the FlowContext.cmp_* methods"""
    def __init__(self, kind):
        self.kind = kind

    def eval(self, ctx):
        w_2 = ctx.popvalue()
        w_1 = ctx.popvalue()
        ctx.pushvalue(ctx.compare(self.kind, w_1, w_2))


# ____________________________________________________________
# Containers

class BuildTuple(Instr):
    def __init__(self, count):
        self.count = count

    def eval(self, ctx):
        items = ctx.popvalues(self.count)
        ctx.pushvalue(op.newtuple(*items).eval(ctx))


class BuildList(Instr):
    def __init__(self, count):
        self.count = count

    def eval(self, ctx):
        items = ctx.popvalues(self.count)
        ctx.pushvalue(op.newlist(*items).eval(ctx))


class BuildListFromArg(Instr):
    def eval(self, ctx):
        last_val = ctx.popvalue()
        ctx.pushvalue(op.newlist().eval(ctx))
        ctx.pushvalue(last_val)


class BuildMap(Instr):
    def eval(self, ctx):
        ctx.pushvalue(op.newdict().eval(ctx))


class BuildSlice(Instr):
    def __init__(self, has_step):
        self.has_step = has_step

    def eval(self, ctx):
        w_step = ctx.popvalue() if self.has_step else w_None
        w_end = ctx.popvalue()
        w_start = ctx.popvalue()
        ctx.pushvalue(op.newslice(w_start, w_end, w_step).eval(ctx))


class ListAppend(Instr):
    """Append the top item to the list found 'depth' items below it."""
    def __init__(self, depth):
        self.depth = depth

    def eval(self, ctx):
        w_value = ctx.popvalue()
        w_list = ctx.peekvalue(self.depth - 1)
        w_append_meth = op.getattr(w_list, const('append')).eval(ctx)
        op.simple_call(w_append_meth, w_value).eval(ctx)


class StoreMap(Instr):
    def eval(self, ctx):
        w_key = ctx.popvalue()
        w_value = ctx.popvalue()
        w_dict = ctx.peekvalue()
        op.setitem(w_dict, w_key, w_value).eval(ctx)


class StoreSubscr(Instr):
    def eval(self, ctx):
        w_subscr = ctx.popvalue()
        w_obj = ctx.popvalue()
        w_newvalue = ctx.popvalue()
        op.setitem(w_obj, w_subscr, w_newvalue).eval(ctx)


class DeleteSubscr(Instr):
    def eval(self, ctx):
        w_subscr = ctx.popvalue()
        w_obj = ctx.popvalue()
        op.delitem(w_obj, w_subscr).eval(ctx)


class _SliceInstr(Instr):
    def __init__(self, has_start, has_stop):
        self.has_start = has_start
        self.has_stop = has_stop

    def pop_bounds(self, ctx):
        w_end = ctx.popvalue() if self.has_stop else w_None
        w_start = ctx.popvalue() if self.has_start else w_None
        return w_start, w_end


class GetSlice(_SliceInstr):
    def eval(self, ctx):
        w_start, w_end = self.pop_bounds(ctx)
        w_obj = ctx.popvalue()
        ctx.pushvalue(op.getslice(w_obj, w_start, w_end).eval(ctx))


class StoreSlice(_SliceInstr):
    def eval(self, ctx):
        w_start, w_end = self.pop_bounds(ctx)
        w_obj = ctx.popvalue()
        w_newvalue = ctx.popvalue()
        op.setslice(w_obj, w_start, w_end, w_newvalue).eval(ctx)


class DeleteSlice(_SliceInstr):
    def eval(self, ctx):
        w_start, w_end = self.pop_bounds(ctx)
        w_obj = ctx.popvalue()
        op.delslice(w_obj, w_start, w_end).eval(ctx)


class UnpackSequence(Instr):
    def __init__(self, count):
        self.count = count

    def eval(self, ctx):
        w_iterable = ctx.popvalue()
        items = ctx.unpack_sequence(w_iterable, self.count)
        for w_item in reversed(items):
            ctx.pushvalue(w_item)


# ____________________________________________________________
# Calls and functions

class Py2Call(Instr):
    """Call with keyword arguments passed as (name, value) pairs on the
    stack, above the positional arguments."""
    def __init__(self, nargs, nkeywords, has_star, has_starstar):
        self.nargs = nargs
        self.nkeywords = nkeywords
        self.has_star = has_star
        self.has_starstar = has_starstar

    def eval(self, ctx):
        w_starstar = ctx.popvalue() if self.has_starstar else None
        w_star = ctx.popvalue() if self.has_star else None
        if w_starstar is not None:
            raise FlowingError("Dict-unpacking is not RPython")
        keywords = {}
        for _ in range(self.nkeywords):
            w_value = ctx.popvalue()
            w_key = ctx.popvalue()
            keywords[w_key.value] = w_value
        arguments = ctx.popvalues(self.nargs)
        w_function = ctx.popvalue()
        ctx.pushvalue(ctx.call_function(w_function, arguments, keywords,
                                        w_star))


class MakeFunction(Instr):
    def __init__(self, ndefaults):
        self.ndefaults = ndefaults

    def eval(self, ctx):
        w_codeobj = ctx.popvalue()
        defaults = ctx.popvalues(self.ndefaults)
        ctx.pushvalue(ctx.newfunction(w_codeobj, defaults))
