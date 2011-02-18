import py
import re
import os.path
from pypy.tool.jitlogparser.parser import parse, Function
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

    def by_filename(self, filename, **kwds):
        return [loop for loop in self.loops
                if loop.filename == filename and self._filter(loop, **kwds)]

    def by_id(self, id, **kwds):
        return [loop for loop in self.loops
                if loop.has_id(id) and self._filter(loop, **kwds)]


class LoopWithIds(Function):

    is_entry_bridge = False

    def __init__(self, *args, **kwds):
        Function.__init__(self, *args, **kwds)
        self.compute_ids()

    @classmethod
    def from_trace(cls, trace, storage):
        res = cls.from_operations(trace.operations, storage)
        res.is_entry_bridge = 'entry bridge' in trace.comment
        return res

    def compute_ids(self):
        self.ids = set()
        self.code = None
        if not self.filename:
            return
        self.code = self.chunks[0].getcode()
        ids = find_ids(self.code)
        all_my_opcodes = self.get_set_of_opcodes()
        # XXX: for now, we just look for the first opcode in the id range
        for id, opcodes in ids.iteritems():
            targetop = opcodes[0]
            if targetop in all_my_opcodes:
                self.ids.add(id)

    def get_set_of_opcodes(self):
        res = set()
        for chunk in self.chunks:
            opcode = self.code.map[chunk.bytecode_no]
            res.add(opcode)
        return res

    def has_id(self, id):
        return id in self.ids
