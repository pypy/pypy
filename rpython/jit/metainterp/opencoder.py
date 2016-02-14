
from rpython.jit.metainterp.history import ConstInt, Const, AbstractDescr,\
    AbstractValue
from rpython.jit.metainterp.resoperation import AbstractResOp, AbstractInputArg,\
    ResOperation, oparity, opname, rop, ResOperation, opwithdescr
from rpython.rlib.rarithmetic import intmask

TAGINT, TAGCONST, TAGBOX = range(3)
TAGMASK = 0x3
TAGSHIFT = 2
MAXINT = 65536

class TraceIterator(object):
    def __init__(self, trace, end):
        self.trace = trace
        self.inpargs = trace._inpargs
        self.pos = 0
        self._count = 0
        self.end = end
        self._cache = [None] * trace._count

    def _get(self, i):
        if i < 0:
            return self.inpargs[-i-1]
        res = self._cache[i]
        assert res is not None
        return res

    def done(self):
        return self.pos >= self.end

    def _next(self):
        res = self.trace._ops[self.pos]
        self.pos += 1
        return res

    def _untag(self, tagged):
        tag, v = untag(tagged)
        if tag == TAGBOX:
            return self._get(v)
        elif tag == TAGINT:
            return ConstInt(v)
        else:
            yyyy

    def next(self):
        pos = self.pos
        opnum = self._next()
        if oparity[opnum] == -1:
            argnum = self._next()
        else:
            argnum = oparity[opnum]
        args = []
        for i in range(argnum):
            args.append(self._untag(self._next()))
        if opwithdescr[opnum]:
            xxx
        else:
            descr = None
        res = ResOperation(opnum, args, -1, descr=descr)
        self._cache[self._count] = res
        self._count += 1
        return res

class Trace(object):
    def __init__(self, inputargs):
        self._ops = []
        for i, inparg in enumerate(inputargs):
            inparg.position = -i - 1
        self._count = 0
        self._inpargs = inputargs

    def _record_op(self, opnum, argboxes, descr=None):
        operations = self._ops
        pos = len(operations)
        operations.append(opnum)
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

    def get_iter(self):
        return TraceIterator(self, len(self._ops))

    def _get_operations(self):
        """ NOT_RPYTHON
        """
        l = []
        i = self.get_iter()
        while not i.done():
            l.append(i.next())
        return l

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
