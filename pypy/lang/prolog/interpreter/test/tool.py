import py
from pypy.lang.prolog.interpreter.error import UnificationFailed, FunctionNotFound
from pypy.lang.prolog.interpreter.parsing import parse_query_term, get_engine
from pypy.lang.prolog.interpreter.engine import Continuation, Heap, Engine

def assert_true(query, e=None):
    if e is None:
        e = Engine()
    term = e.parse(query)[0][0]
    e.run(term)
    f = Heap()
    f.vars = e.heap.vars[:]
    return f

def assert_false(query, e=None):
    if e is None:
        e = Engine()
    term = e.parse(query)[0][0]
    py.test.raises(UnificationFailed, e.run, term)

def prolog_raises(exc, query, e=None):
    return assert_true("catch(((%s), fail), error(%s), true)." %
                       (query, exc), e)

class CollectAllContinuation(Continuation):
    def __init__(self):
        self.heaps = []

    def call(self, engine):
        f = Heap()
        f.vars = engine.heap.vars[:]
        self.heaps.append(f)
#        import pdb; pdb.set_trace()
        print "restarting computation"
        raise UnificationFailed

def collect_all(engine, s):
    collector = CollectAllContinuation()
    term = engine.parse(s)[0][0]
    py.test.raises(UnificationFailed, engine.run, term,
                   collector)
    return collector.heaps

