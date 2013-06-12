import py
import sys
import re
import os.path
try:
    from _pytest.assertion import newinterpret
except ImportError:   # e.g. Python 2.5
    newinterpret = None

from rpython.tool.jitlogparser.parser import SimpleParser, Function, TraceForOpcode
from rpython.tool.jitlogparser.storage import LoopStorage


class Log(object):
    def __init__(self, rawtraces):
        storage = LoopStorage()
        traces = [SimpleParser.parse_from_input(rawtrace) for rawtrace in rawtraces]
        traces = storage.reconnect_loops(traces)
        self.loops = [LoopWithIds.from_trace(trace, storage) for trace in traces]

    def _filter(self, loop, is_entry_bridge=False):
        return is_entry_bridge == '*' or loop.is_entry_bridge == is_entry_bridge

    def filter_loops(self, function="", **kwds):
        return [loop for loop in self.loops
                    if function in loop.chunks[0].bytecode_name and
                        self._filter(loop, **kwds)]

    @classmethod
    def opnames(self, oplist):
        return [op.name for op in oplist]

class LoopWithIds(Function):

    is_entry_bridge = False

    def __init__(self, *args, **kwds):
        Function.__init__(self, *args, **kwds)

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

    def get_set_of_opcodes(self):
        result = set()
        for chunk in self.chunks:
            if isinstance(chunk, TraceForOpcode):
                opcode = chunk.getopcode()
                result.add(opcode)
        return result

    def _ops_for_chunk(self, chunk, include_debug_merge_points):
        for op in chunk.operations:
            if op.name != 'debug_merge_point' or include_debug_merge_points:
                yield op

    def _allops(self, include_debug_merge_points=False, opcode=None):
        opcode_name = opcode
        for chunk in self.flatten_chunks():
            opcode = chunk.getopcode()
            if opcode_name is None or \
                   (opcode and opcode.__class__.__name__ == opcode_name):
                for op in self._ops_for_chunk(chunk, include_debug_merge_points):
                    yield op

    def allops(self, *args, **kwds):
        return list(self._allops(*args, **kwds))

    def format_ops(self, **kwds):
        ops = self.allops(**kwds)
        return '\n'.join(map(str, ops))

    def print_ops(self, *args, **kwds):
        print self.format_ops(*args, **kwds)

    def match(self, expected_src, **kwds):
        ops = list(self.allops())
        matcher = OpMatcher(ops, src=self.format_ops())
        return matcher.match(expected_src, **kwds)

class InvalidMatch(Exception):
    opindex = None

    def __init__(self, message, frame):
        Exception.__init__(self, message)
        # copied and adapted from pytest's magic AssertionError
        f = py.code.Frame(frame)
        try:
            source = f.code.fullsource
            if source is not None:
                try:
                    source = source.getstatement(f.lineno)
                except IndexError:
                    source = None
                else:
                    source = str(source.deindent()).strip()
        except py.error.ENOENT:
            source = None
        if source and source.startswith('self._assert(') and newinterpret:
            # transform self._assert(x, 'foo') into assert x, 'foo'
            source = source.replace('self._assert(', 'assert ')
            source = source[:-1] # remove the trailing ')'
            self.msg = newinterpret.interpret(source, f, should_fail=True)
        else:
            self.msg = "<could not determine information>"


class OpMatcher(object):

    def __init__(self, ops, src=None):
        self.ops = ops
        self.src = src
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
        if ' = ' in line:
            resvar, _, line = line.partition(' = ')
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
        if args == ['']:
            args = []
        if args and args[-1].startswith('descr='):
            descr = args.pop()
            descr = descr[len('descr='):]
        else:
            descr = None
        return opname, resvar, args, descr

    @classmethod
    def preprocess_expected_src(cls, src):
        return src

    @classmethod
    def is_const(cls, v1):
        return isinstance(v1, str) and v1.startswith('ConstClass(')

    def match_var(self, v1, exp_v2):
        assert v1 != '_'
        if exp_v2 == '_':
            return True
        if self.is_const(v1) or self.is_const(exp_v2):
            return v1[:-1].startswith(exp_v2[:-1])
        if v1 not in self.alpha_map:
            self.alpha_map[v1] = exp_v2
        return self.alpha_map[v1] == exp_v2

    def match_descr(self, descr, exp_descr):
        if descr == exp_descr or exp_descr == '...':
            return True
        self._assert(exp_descr is not None and re.match(exp_descr, descr), "descr mismatch")

    def _assert(self, cond, message):
        if not cond:
            raise InvalidMatch(message, frame=sys._getframe(1))

    def match_op(self, op, (exp_opname, exp_res, exp_args, exp_descr)):
        self._assert(op.name == exp_opname, "operation mismatch")
        self.match_var(op.res, exp_res)
        if exp_args != ['...']:
            self._assert(len(op.args) == len(exp_args), "wrong number of arguments")
            for arg, exp_arg in zip(op.args, exp_args):
                self._assert(self.match_var(arg, exp_arg), "variable mismatch: %r instead of %r" % (arg, exp_arg))
        self.match_descr(op.descr, exp_descr)


    def _next_op(self, iter_ops, assert_raises=False):
        try:
            op = iter_ops.next()
        except StopIteration:
            self._assert(assert_raises, "not enough operations")
            return
        else:
            self._assert(not assert_raises, "operation list too long")
            return op

    def match_until(self, until_op, iter_ops):
        while True:
            op = self._next_op(iter_ops)
            try:
                # try to match the op, but be sure not to modify the
                # alpha-renaming map in case the match does not work
                alpha_map = self.alpha_map.copy()
                self.match_op(op, until_op)
            except InvalidMatch:
                # it did not match: rollback the alpha_map, and just skip this
                # operation
                self.alpha_map = alpha_map
            else:
                # it matched! The '...' operator ends here
                return op

    def match_loop(self, expected_ops, ignore_ops):
        """
        A note about partial matching: the '...' operator is non-greedy,
        i.e. it matches all the operations until it finds one that matches
        what is after the '...'
        """
        iter_exp_ops = iter(expected_ops)
        iter_ops = iter(self.ops)
        for opindex, exp_op in enumerate(iter_exp_ops):
            try:
                if exp_op == '...':
                    # loop until we find an operation which matches
                    try:
                        exp_op = iter_exp_ops.next()
                    except StopIteration:
                        # the ... is the last line in the expected_ops, so we just
                        # return because it matches everything until the end
                        return
                    op = self.match_until(exp_op, iter_ops)
                else:
                    while True:
                        op = self._next_op(iter_ops)
                        if op.name not in ignore_ops:
                            break
                self.match_op(op, exp_op)
            except InvalidMatch, e:
                e.opindex = opindex
                raise
        #
        # make sure we exhausted iter_ops
        self._next_op(iter_ops, assert_raises=True)

    def match(self, expected_src, ignore_ops=[]):
        def format(src, opindex=None):
            if src is None:
                return ''
            text = str(py.code.Source(src).deindent().indent())
            lines = text.splitlines(True)
            if opindex is not None and 0 <= opindex < len(lines):
                lines[opindex] = lines[opindex].rstrip() + '\t<=====\n'
            return ''.join(lines)
        #
        expected_src = self.preprocess_expected_src(expected_src)
        expected_ops = self.parse_ops(expected_src)
        try:
            self.match_loop(expected_ops, ignore_ops)
        except InvalidMatch, e:
            #raise # uncomment this and use py.test --pdb for better debugging
            print '@' * 40
            print "Loops don't match"
            print "================="
            print e.args
            print e.msg
            print
            print "Ignore ops:", ignore_ops
            print "Got:"
            print format(self.src, e.opindex)
            print
            print "Expected:"
            print format(expected_src)
            return False
        else:
            return True

