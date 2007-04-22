import os
import py

from py.magic import greenlet
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.rstack import yield_current_heap_to_caller
from pypy.translator.c.test.test_stackless import StacklessTest

from pypy.lang.prolog.interpreter.error import UnificationFailed, CutException

def make_llheap(choice_point, func, args):
    llheap = yield_current_heap_to_caller()
    try:
        choice_point.current = llheap
        try:
            func(*args)
        except UnificationFailed:
            choice_point.no_choice()
        except Exception, e:
            choice_point.exception = e
        choice_point.switch_back()
    except:
        pass
    os.write(0, "bad\n")
    return llheap # will nexer be executed, help the translator
make_llheap._annspecialcase_ = "specialize:arg(1)"

class ChoicePoint(object):
    def __init__(self, engine, continuation, stop_cut=False):
        self._init_current()
        self.engine = engine
        self.oldstate = engine.heap.branch()
        self.continuation = continuation
        self.stop_cut = stop_cut
        self.any_choice = True
        self.exception = None

    def _init_current(self):
        if we_are_translated():
            self.current = None
        else:
            self.current = greenlet.getcurrent()

    def choose(self, last=False):
        try:
            self.do_continue()
        except CutException, e:
            if self.stop_cut:
                self.continuation = e.continuation
            else:
                self.exception = e
        except UnificationFailed:
            self.engine.heap.revert(self.oldstate)
            if last:
                raise
            return
        self.switch_back()
        assert 0

    def chooselast(self):
        self.do_continue()

    def no_choice(self):
        self.exception = UnificationFailed()

    def switch(self, func, *args):
        if we_are_translated():
            llheap = make_llheap(self, func, args)
            llheap.switch()
        else:
            g = greenlet(func)
            try:
                g.switch(*args)
            except UnificationFailed:
                self.no_choice()
        if self.exception is not None:
            raise self.exception
    switch._annspecialcase_ = "specialize:arg(1)"

    def switch_back(self):
        self.current.switch()

    def do_continue(self):
        self.continuation.run(self.engine)

class RuleChoicePoint(ChoicePoint):
    def __init__(self, query, engine, continuation, stop_cut=False):
        ChoicePoint.__init__(self, engine, continuation, stop_cut)
        self.query = query
        self.rule = None

    def choose_rule(self, rule):
        self.rule = rule
        self.choose()

    def choose_last_rule(self, rule):
        self.rule = rule
        self.chooselast()

    def do_continue(self):
        continuation = self.continuation
        self.engine.try_rule(self.rule, self.query, continuation)
