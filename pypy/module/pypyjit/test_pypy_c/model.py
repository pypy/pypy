import py
import re
import os.path
from lib_pypy import disassembler
from pypy.tool.jitlogparser.parser import parse, Function
from pypy.tool.jitlogparser.storage import LoopStorage

class Log(object):
    def __init__(self, func, rawtraces):
        storage = LoopStorage()
        storage.ids = self.find_ids(func)
        traces = [parse(rawtrace) for rawtrace in rawtraces]
        traces = storage.reconnect_loops(traces)
        self.loops = [LoopWithIds.from_trace(trace, storage) for trace in traces]

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

    def _filter(self, loop, is_entry_bridge=False):
        return is_entry_bridge == '*' or loop.is_entry_bridge == is_entry_bridge

    def by_filename(self, filename, **kwds):
        return [loop for loop in self.loops
                if loop.filename == filename and self._filter(loop, **kwds)]


class LoopWithIds(Function):

    is_entry_bridge = False

    @classmethod
    def from_trace(cls, trace, storage):
        res = cls.from_operations(trace.operations, storage)
        if 'entry bridge' in trace.comment:
            res.is_entry_bridge = True
        return res
