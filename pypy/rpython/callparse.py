from pypy.interpreter.pycode import cpython_code_signature
from pypy.interpreter.argument import Arguments, ArgErr
from pypy.annotation import model as annmodel
from pypy.rpython import rtuple

class CallPatternTooComplex(Exception):
    pass


# for parsing call arguments
class RPythonCallsSpace:
    """Pseudo Object Space providing almost no real operation.
    For the Arguments class: if it really needs other operations, it means
    that the call pattern is too complex for R-Python.
    """
    def newtuple(self, items):
        return NewTupleHolder(items)

    def newdict(self, stuff):
        raise CallPatternTooComplex, "'**' argument"

    def unpackiterable(self, it, expected_length=None):
        if it.is_tuple():
            items = it.items()
            if (expected_length is not None and
                expected_length != len(items)):
                raise ValueError
            return items
        raise CallPatternTooComplex, "'*' argument must be a tuple"


def callparse(op, func, rinputs, hop):
    space = RPythonCallsSpace()
    def args_h(start):
        return [VarHolder(i, hop.args_s[i]) for i in range(start, hop.nb_args)]
    if op == "simple_call":
        arguments =  Arguments(space, args_h(1))
    elif op == "call_args":
        arguments = Arguments.fromshape(space, hop.args_s[1].const, # shape
                                        args_h(2))
    # parse the arguments according to the function we are calling
    signature = cpython_code_signature(func.func_code)
    defs_h = []
    if func.func_defaults:
        for x in func.func_defaults:
            defs_h.append(ConstHolder(x))
    try:
        holders = arguments.match_signature(signature, defs_h)
    except ArgErr, e:
        raise TypeError, "signature mismatch: %s" % e.getmsg(arguments, func.__name__)

    assert len(holders) == len(rinputs), "argument parsing mismatch"
    vlist = []
    for h,r in zip(holders, rinputs):
        v = h.emit(r, hop)
        vlist.append(v)
    return vlist


class Holder(object):

    def is_tuple(self):
        return False

    def emit(self, repr, hop):
        try:
            cache = self._cache
        except AttributeError:
            cache = self._cache = {}
        try:
            return cache[repr]
        except KeyError:
            v = self._emit(repr, hop)
            cache[repr] = v
            return v
    

class VarHolder(Holder):

    def __init__(self, num, s_obj):
        self.num = num
        self.s_obj = s_obj

    def is_tuple(self):
        return isinstance(self.s_obj, annmodel.SomeTuple)

    def items(self):
        assert self.is_tuple()
        n = len(self.s_obj.items)
        return tuple([ItemHolder(self, i) for i in range(n)])
        
    def _emit(self, repr, hop):
        return hop.inputarg(repr, arg=self.num)

    def access(self, hop):
        repr = hop.args_r[self.num]
        return repr, self.emit(repr, hop)

class ConstHolder(Holder):
    def __init__(self, value):
        self.value = value

    def is_tuple(self):
        return type(self.value) is tuple

    def items(self):
        assert self.is_tuple()
        return self.value

    def _emit(self, repr, hop):
        return hop.inputconst(repr, self.value)


class NewTupleHolder(Holder):
    def __new__(cls, holders):
        for h in holders:
            if not isinstance(h, ItemHolder) or not h.holder == holders[0].holder:
                break
        else:
            if 0 < len(holders) == len(holders[0].holder.items()):
                return h[0].holder
        inst = Holder.__new__(cls)
        inst.holders = tuple(holders)
        return inst

    def is_tuple(self):
        return True

    def items(self):
        return self.holders

    def _emit(self, repr, hop):
        assert isinstance(repr, rtuple.TupleRepr)
        tupleitems_v = []
        for h in self.holders:
            v = h.emit(repr.items_r[len(tupleitems_v)], hop)
            tupleitems_v.append(v)
        vtuple = rtuple.newtuple(hop.llops, repr, tupleitems_v)
        return vtuple


class ItemHolder(Holder):
    def __init__(self, holder, index):
        self.holder = holder
        self.index = index

    def _emit(self, repr, hop):
        index = self.index
        r_tup, v_tuple = self.holder.access(hop)
        v = r_tup.getitem(hop, v_tuple, index)
        return hop.llops.convertvar(v, r_tup.items_r[index], repr)
