import py
import re
import os.path
from pypy.tool.jitlogparser.parser import parse, Function, TraceForOpcode
from pypy.tool.jitlogparser.storage import LoopStorage


def find_ids_range(code):
    """
    Parse the given function and return a dictionary mapping "ids" to
    "line ranges".  Ids are identified by comments with a special syntax::

        # "myid" corresponds to the whole line
        print 'foo' # ID: myid
    """
    result = {}
    start_lineno = code.co.co_firstlineno
    for i, line in enumerate(py.code.Source(code.source)):
        m = re.search('# ID: (\w+)', line)
        if m:
            name = m.group(1)
            lineno = start_lineno+i
            result[name] = xrange(lineno, lineno+1)
    return result

def find_ids(code):
    """
    Parse the given function and return a dictionary mapping "ids" to
    "opcodes".
    """
    ids = {}
    ranges = find_ids_range(code)
    for name, linerange in ranges.iteritems():
        opcodes = [opcode for opcode in code.opcodes
                   if opcode.lineno in linerange]
        ids[name] = opcodes
    return ids


class Log(object):
    def __init__(self, func, rawtraces):
        storage = LoopStorage()
        traces = [parse(rawtrace) for rawtrace in rawtraces]
        traces = storage.reconnect_loops(traces)
        self.loops = [LoopWithIds.from_trace(trace, storage) for trace in traces]

    def _filter(self, loop, is_entry_bridge=False):
        return is_entry_bridge == '*' or loop.is_entry_bridge == is_entry_bridge

    def loops_by_filename(self, filename, **kwds):
        """
        Return all loops which start in the file ``filename``
        """
        return [loop for loop in self.loops
                if loop.filename == filename and self._filter(loop, **kwds)]

    def loops_by_id(self, id, **kwds):
        """
        Return all loops which contain the ID ``id``
        """
        return [loop for loop in self.loops
                if loop.has_id(id) and self._filter(loop, **kwds)]

    @classmethod
    def opnames(self, oplist):
        return [op.name for op in oplist]

class LoopWithIds(Function):

    is_entry_bridge = False

    def __init__(self, *args, **kwds):
        Function.__init__(self, *args, **kwds)
        self.ids = {}
        self.code = self.chunks[0].getcode()
        if self.code:
            self.compute_ids(self.ids)

    @classmethod
    def from_trace(cls, trace, storage):
        res = cls.from_operations(trace.operations, storage)
        res.is_entry_bridge = 'entry bridge' in trace.comment
        return res

    def flatten_chunks(self):
        """
        return a flat sequence of TraceForOpcode objects, including the ones
        inside inlined functions
        """
        for chunk in self.chunks:
            if isinstance(chunk, TraceForOpcode):
                yield chunk
            else:
                for subchunk in chunk.flatten_chunks():
                    yield subchunk

    def compute_ids(self, ids):
        #
        # 1. compute the ids of self, i.e. the outer function
        id2opcodes = find_ids(self.code)
        all_my_opcodes = self.get_set_of_opcodes()
        # XXX: for now, we just look for the first opcode in the id range
        for id, opcodes in id2opcodes.iteritems():
            if not opcodes:
                continue
            target_opcode = opcodes[0]
            if target_opcode in all_my_opcodes:
                ids[id] = opcodes
        #
        # 2. compute the ids of all the inlined functions
        for chunk in self.chunks:
            if isinstance(chunk, LoopWithIds):
                chunk.compute_ids(ids)

    def get_set_of_opcodes(self):
        result = set()
        for chunk in self.chunks:
            if isinstance(chunk, TraceForOpcode):
                opcode = chunk.getopcode()
                result.add(opcode)
        return result

    def has_id(self, id):
        return id in self.ids

    def _ops_for_chunk(self, chunk, include_debug_merge_points):
        for op in chunk.operations:
            if op.name != 'debug_merge_point' or include_debug_merge_points:
                yield op

    def allops(self, include_debug_merge_points=False):
        for chunk in self.flatten_chunks():
            for op in self._ops_for_chunk(chunk, include_debug_merge_points):
                yield op

    def print_ops(self, id=None):
        if id is None:
            ops = self.allops()
        else:
            ops = self.ops_by_id(id)
        print '\n'.join(map(str, ops))

    def ops_by_id(self, id, include_debug_merge_points=False, opcode=None):
        opcode_name = opcode
        target_opcodes = self.ids[id]
        for chunk in self.flatten_chunks():
            opcode = chunk.getopcode()
            if opcode in target_opcodes and (opcode_name is None or
                                             opcode.__class__.__name__ == opcode_name):
                for op in self._ops_for_chunk(chunk, include_debug_merge_points):
                    yield op

    def match(self, expected_src):
        ops = list(self.allops())
        matcher = OpMatcher(ops)
        return matcher.match(expected_src)

    def match_by_id(self, id, expected_src):
        ops = list(self.ops_by_id(id))
        matcher = OpMatcher(ops)
        return matcher.match(expected_src)

class InvalidMatch(Exception):
    pass

class OpMatcher(object):

    def __init__(self, ops):
        self.ops = ops
        self.alpha_map = {}

    @classmethod
    def parse_ops(cls, src):
        ops = [cls.parse_op(line) for line in src.splitlines()]
        return [op for op in ops if op is not None]

    @classmethod
    def parse_op(cls, line):
        # strip comment
        if '#' in line:
            line = line[:line.index('#')]
        # find the resvar, if any
        if '=' in line:
            resvar, _, line = line.partition('=')
            resvar = resvar.strip()
        else:
            resvar = None
        line = line.strip()
        if not line:
            return None
        if line == '...':
            return line
        opname, _, args = line.partition('(')
        opname = opname.strip()
        assert args.endswith(')')
        args = args[:-1]
        args = args.split(',')
        args = map(str.strip, args)
        return opname, resvar, args

    @classmethod
    def preprocess_expected_src(cls, src):
        # all loops decrement the tick-counter at the end. The rpython code is
        # in jump_absolute() in pypyjit/interp.py. The string --TICK-- is
        # replaced with the corresponding operations, so that tests don't have
        # to repeat it every time
        ticker_check = """
            ticker0 = getfield_raw(ticker_address)
            ticker1 = int_sub(ticker0, 1)
            setfield_raw(ticker_address, ticker1)
            ticker_cond = int_lt(ticker1, 0)
            guard_false(ticker_cond)
        """
        src = src.replace('--TICK--', ticker_check)
        return src

    @classmethod
    def is_const(cls, v1):
        return isinstance(v1, str) and v1.startswith('ConstClass(')
    
    def match_var(self, v1, v2):
        if self.is_const(v1) or self.is_const(v2):
            return v1 == v2
        if v1 not in self.alpha_map:
            self.alpha_map[v1] = v2
        return self.alpha_map[v1] == v2

    def _assert(self, cond, message):
        if not cond:
            raise InvalidMatch(message)

    def match_op(self, op, (exp_opname, exp_res, exp_args)):
        self._assert(op.name == exp_opname, "operation mismatch")
        self.match_var(op.res, exp_res)
        self._assert(len(op.args) == len(exp_args), "wrong number of arguments")
        for arg, exp_arg in zip(op.args, exp_args):
            self._assert(self.match_var(arg, exp_arg), "variable mismatch")

    def _next_op(self, iter_ops, message, assert_raises=False):
        try:
            op = iter_ops.next()
        except StopIteration:
            self._assert(assert_raises, message)
            return
        else:
            self._assert(not assert_raises, message)
            return op

    def match_loop(self, expected_ops):
        iter_exp_ops = iter(expected_ops)
        iter_ops = iter(self.ops)
        for exp_op in iter_exp_ops:
            op = self._next_op(iter_ops, "not enough operations")
            self.match_op(op, exp_op)
        #
        # make sure we exhausted iter_ops
        self._next_op(iter_ops, "operation list too long", assert_raises=True)

    def match(self, expected_src):
        expected_src = self.preprocess_expected_src(expected_src)
        expected_ops = self.parse_ops(expected_src)
        try:
            self.match_loop(expected_ops)
        except InvalidMatch:
            #raise # uncomment this and use py.test --pdb for better debugging
            return False
        else:
            return True

