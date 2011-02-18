import py
import re
from lib_pypy import disassembler
from pypy.jit.tool import oparser

class Log(object):
    def __init__(self, func, rawtraces):
        chunks = self.find_chunks(func)
        self.traces = [Trace(rawtrace, chunks) for rawtrace in rawtraces]

    @classmethod
    def find_chunks_range(cls, func):
        """
        Parse the given function and return a dictionary mapping "chunk
        names" to "line ranges".  Chunks are identified by comments with a
        special syntax::

            # the chunk "myid" corresponds to the whole line
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
    def find_chunks(cls, func):
        """
        Parse the given function and return a dictionary mapping "chunk names"
        to "opcodes".
        """
        chunks = {}
        code = disassembler.dis(func)
        ranges = cls.find_chunks_range(func)
        for name, linerange in ranges.iteritems():
            opcodes = [opcode for opcode in code.opcodes
                       if opcode.lineno in linerange]
            chunks[name] = opcodes
        return chunks


class Trace(object):
    def __init__(self, rawtrace, chunks):
        # "low level trace", i.e. an instance of history.TreeLoop
        self.lltrace = oparser.parse(rawtrace, no_namespace=True)
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
