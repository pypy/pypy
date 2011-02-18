import py
import re
from lib_pypy import disassembler
from pypy.tool.jitlogparser.parser import parse, slice_debug_merge_points
from pypy.tool.jitlogparser.storage import LoopStorage

class Log(object):
    def __init__(self, func, rawtraces):
        chunks = self.find_chunks(func)
        self.traces = [Trace(rawtrace, chunks) for rawtrace in rawtraces]

    @classmethod
    def find_ids_range(cls, func):
        """
        Parse the given function and return a dictionary mapping "ids" to
        "line ranges".  Ids are identified by comments with a special syntax::

            # "myid" corresponds to the whole line
            print 'foo' # ID: myid
        """
        result = {}
        start_lineno = func.func_code.co_firstlineno
        for i, line in enumerate(py.code.Source(func)):
            m = re.search('# ID: (\w+)', line)
            if m:
                name = m.group(1)
                lineno = start_lineno+i
                result[name] = xrange(lineno, lineno+1)
        return result

    @classmethod
    def find_ids(cls, func):
        """
        Parse the given function and return a dictionary mapping "ids" to
        "opcodes".
        """
        ids = {}
        code = disassembler.dis(func)
        ranges = cls.find_ids_range(func)
        for name, linerange in ranges.iteritems():
            opcodes = [opcode for opcode in code.opcodes
                       if opcode.lineno in linerange]
            ids[name] = opcodes
        return ids


class Trace(object):
    def __init__(self, rawtrace, chunks):
        # "low level trace", i.e. an instance of history.TreeLoop
        self.lltrace = parse(rawtrace)
        storage = LoopStorage()
        function = slice_debug_merge_points(self.lltrace.operations, storage)
        import pdb;pdb.set_trace()
        self.split_into_opcodes()

    def split_into_opcodes(self):
        self.opcodes = []
        for op in self.lltrace.operations:
            if op.getopname() == "debug_merge_point":
                opcode = TraceForOpcode(op) # XXX
                self.opcodes.append(opcode)
            else:
                opcode.append(op)

class TraceForOpcode(list):
    pass
