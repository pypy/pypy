import py
import os
from prolog.interpreter.error import UnificationFailed
from prolog.interpreter.parsing import parse_query_term, get_engine
from prolog.interpreter.continuation import Continuation, Heap, Engine
from prolog.interpreter.parsing import parse_file, TermBuilder

def assert_true(query, e=None):
    if e is None:
        e = Engine()
    terms, vars = e.parse(query)
    term, = terms
    e.run(term, e.modulewrapper.current_module)
    return dict([(name, var.dereference(None))
                     for name, var in vars.iteritems()])

def assert_false(query, e=None):
    if e is None:
        e = Engine()
    term = e.parse(query)[0][0]
    py.test.raises(UnificationFailed, e.run, term, e.modulewrapper.current_module)

def prolog_raises(exc, query, e=None):
    prolog_catch = "catch(((%s), fail), error(%s), true)." % (query, exc)
    return assert_true(prolog_catch, e)

class CollectAllContinuation(Continuation):
    nextcont = None
    def __init__(self, module, vars):
        self.heaps = []
        self.vars = vars
        self._candiscard = True
        self.module = module

    def activate(self, fcont, heap):
        self.heaps.append(dict([(name, var.dereference(heap))
                                    for name, var in self.vars.iteritems()]))
        print "restarting computation"
        raise UnificationFailed

def collect_all(engine, s):
    terms, vars = engine.parse(s)
    term, = terms
    collector = CollectAllContinuation(engine.modulewrapper.user_module, vars)
    py.test.raises(UnificationFailed, engine.run, term,
            engine.modulewrapper.current_module, collector)
    return collector.heaps

def parse(inp):
    t = parse_file(inp)
    builder = TermBuilder()
    return builder.build(t)

def create_file(name, content):
    fd = os.open(name, os.O_CREAT|os.O_RDWR, 0666)
    os.write(fd, content)
    os.close(fd)

def delete_file(name):
    os.unlink(name)

def create_dir(name):
    os.mkdir(name)

def delete_dir(name):
    current_dir = os.path.abspath(name)
    items = os.listdir(current_dir)
    for item in items:
        abspath = current_dir + "/" + item
        if os.path.isfile(abspath):
            delete_file(abspath)
        else:
            delete_dir(abspath)
    os.rmdir(current_dir)

def file_content(src):
    f = open(src)
    data = f.read()
    f.close()
    return data

