
from rpython.jit.metainterp.history import ConstInt, Const, AbstractDescr,\
    AbstractValue
from rpython.jit.metainterp.resoperation import AbstractResOp, AbstractInputArg,\
    ResOperation, oparity, opname, rop
from rpython.rlib.rarithmetic import intmask

TAGINT, TAGCONST, TAGBOX, TAGOUTPUT = range(4)
TAGMASK = 0x3
TAGSHIFT = 2
MAXINT = 65536

class TraceIterator(object):
    def __init__(self, trace, end):
        self.trace = trace
        self.pos = trace._start
        self.end = end

    def done(self):
        return self.pos >= self.end

    def _next(self):
        res = self.trace._ops[self.pos]
        self.pos += 1
        return res

    def next(self):
        pos = self.pos
        opnum = self._next()
        self._next() # forwarding
        if oparity[opnum] == -1:
            argnum = self._next()
        else:
            argnum = oparity[opnum]
        args = []
        for i in range(argnum):
            args.append(self._next())
        return RecordedOp(pos, opnum, args)

class RecordedOp(AbstractValue):
    def __init__(self, pos, opnum, args, descr=None):
        self.opnum = opnum
        self.args = args
        self._pos = pos
        self.descr = descr

    def get_tag(self):
        return tag(TAGBOX, self._pos)

    def getarglist(self):
        return self.args

    def getdescr(self):
        return self.descr

    def numargs(self):
        return len(self.args)

    def getopnum(self):
        return self.opnum

    def getarg(self, i):
        return self.args[i]

    def getopname(self):
        try:
            return opname[self.getopnum()].lower()
        except KeyError:
            return '<%d>' % self.getopnum()

    def __hash__(self):
        raise NotImplementedError


class Trace(object):
    def __init__(self, inputargs):
        self._ops = [0] * (2 * len(inputargs)) # place for forwarding inputargs
        # plus infos
        for i, inparg in enumerate(inputargs):
            self._ops[i * 2 + i] = i
            inparg.position = i * 2
        self._start = len(inputargs) * 2
        self._count = len(inputargs)

    def _record_op(self, opnum, argboxes, descr=None):
        operations = self._ops
        pos = len(operations)
        operations.append(opnum)
        operations.append(self._count) # here we keep the index into infos
        if oparity[opnum] == -1:
            operations.append(len(argboxes))
        operations.extend([encode(box) for box in argboxes])
        if descr is not None:
            operations.append(encode(descr))
        self._count += 1
        return pos

    def _record_raw(self, opnum, tagged_args, tagged_descr=-1):
        operations = self._ops
        pos = len(operations)
        operations.append(opnum)
        operations.append(self._count) # here we keep the index into infos
        if oparity[opnum] == -1:
            operations.append(len(tagged_args))
        operations.extend(tagged_args)
        if tagged_descr != -1:
            operations.append(tagged_descr)
        self._count += 1
        return pos        

    def record_forwarding(self, op, newtag):
        index = op._pos
        self._ops[index] = -newtag - 1

    def record_op(self, opnum, argboxes, descr=None):
        # return an ResOperation instance, ideally die in hell
        pos = self._record_op(opnum, argboxes, descr)
        return ResOperation(opnum, argboxes, pos, descr)

    def record_op_tag(self, opnum, tagged_args, descr=None):
        return tag(TAGBOX, self._record_raw(opnum, tagged_args, descr))

    def record_op_output_tag(self, opnum, tagged_args, descr=None):
        return tag(TAGOUTPUT, self._record_raw(opnum, tagged_args, descr))

    def get_info(self, infos, pos):
        index = self._ops[pos + 1]
        return infos[index]

    def set_info(self, infos, pos, info):
        index = self._ops[pos + 1]
        infos[index] = info

    def get_iter(self):
        return TraceIterator(self, len(self._ops))

def tag(kind, pos):
    return (pos << TAGSHIFT) | kind

def untag(tagged):
    return intmask(tagged) & TAGMASK, intmask(tagged) >> TAGSHIFT

def encode(box):
    if isinstance(box, Const):
        if isinstance(box, ConstInt) and box.getint() < MAXINT:
            return tag(TAGINT, box.getint())
        else:
            yyy
    elif isinstance(box, AbstractResOp):
        return tag(TAGBOX, box.position)
    elif isinstance(box, AbstractInputArg):
        return tag(TAGBOX, box.position)
    elif isinstance(box, AbstractDescr):
        pass
    else:
        yyy
