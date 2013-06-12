import py
import time
from rpython.rlib import jit
from rpython.rlib.objectmodel import we_are_translated, specialize
from prolog.interpreter import error
from prolog.interpreter import helper
from prolog.interpreter.term import Term, Atom, BindingVar, Callable, Var
from prolog.interpreter.function import Function, Rule
from prolog.interpreter.heap import Heap
from prolog.interpreter.signature import Signature
from prolog.interpreter.module import Module, ModuleWrapper
from prolog.interpreter.helper import unwrap_predicate_indicator
from prolog.interpreter.stream import StreamWrapper

Signature.register_extr_attr("function", engine=True)

# ___________________________________________________________________
# JIT stuff

def get_printable_location(rule):
    if rule:
        s = rule.signature.string()
    else:
        s = "No rule"
    return s

def get_jitcell_at(where, rule):
    # XXX can be vastly simplified
    return rule.jit_cells.get(where, None)

def set_jitcell_at(newcell, where, rule):
    # XXX can be vastly simplified
    rule.jit_cells[where] = newcell

predsig = Signature.getsignature(":-", 2)
callsig = Signature.getsignature(":-", 1)

jitdriver = jit.JitDriver(
        greens=["rule"],
        reds=["scont", "fcont", "heap"],
        get_printable_location=get_printable_location,
        #get_jitcell_at=get_jitcell_at,
        #set_jitcell_at=set_jitcell_at,
        )

# ___________________________________________________________________
# end JIT stuff


def driver(scont, fcont, heap):
    rule = None
    while not scont.is_done():
        #view(scont=scont, fcont=fcont, heap=heap)
        if isinstance(scont, RuleContinuation) and scont._rule.body is not None:
            rule = scont._rule
            jitdriver.can_enter_jit(rule=rule, scont=scont, fcont=fcont,
                                    heap=heap)
        try:
            jitdriver.jit_merge_point(rule=rule, scont=scont, fcont=fcont,
                                      heap=heap)
            oldscont = scont
            scont, fcont, heap  = scont.activate(fcont, heap)
            assert heap is not None
        except error.UnificationFailed:
            if not we_are_translated():
                if fcont.is_done():
                    raise
            scont, fcont, heap = fcont.fail(heap)
        except error.CatchableError, e:
            scont, fcont, heap = scont.engine.throw(e.term, scont, fcont, heap)
        else:
            scont, fcont, heap = _process_hooks(scont, fcont, heap)
    assert isinstance(scont, DoneSuccessContinuation)

    if scont.failed:
        raise error.UnificationFailed

@jit.unroll_safe
def _process_hooks(scont, fcont, heap):
    if heap.hook:
        e = scont.engine
        hookcell = heap.hook
        heap.hook = None
        while hookcell:
            attvar = hookcell.attvar
            attmap = jit.hint(attvar.attmap, promote=True)
            for i in range(len(attvar.value_list)):
                val = attvar.value_list[i]
                if val is None:
                    continue
                module = attmap.get_attname_at_index(i)
                query = Callable.build("attr_unify_hook", [val, attvar])
                try:
                    mod = e.modulewrapper.get_module(module, query)
                except error.CatchableError, err:
                    scont, fcont, heap = scont.engine.throw(err.term, scont, fcont, heap)
                    break
                scont, fcont, heap = e.call(query, mod, scont, fcont, heap)
                heap.add_trail_atts(attvar, module)
            hookcell = hookcell.next
            attvar.value_list = None # XXX?
    return scont, fcont, heap

class Engine(object):
    def __init__(self, load_system=False):
        self.parser = None
        self.operations = None
        self.modulewrapper = ModuleWrapper(self)
        if load_system:
            self.modulewrapper.init_system_module()
        
        from prolog.builtin.statistics import Clocks
        self.clocks = Clocks()
        self.clocks.startup()
        self.streamwrapper = StreamWrapper()

    def _freeze_(self):
        return True

    # _____________________________________________________
    # database functionality

    def add_rule(self, rule, end=True, old_modname=None):
        m = self.modulewrapper
        if helper.is_term(rule):
            assert isinstance(rule, Callable)
            if rule.signature().eq(predsig):
                rule = Rule(rule.argument_at(0), rule.argument_at(1),
                        m.current_module)
            else:
                rule = Rule(rule, None, m.current_module)
        elif isinstance(rule, Atom):
            rule = Rule(rule, None, m.current_module)
        else:
            error.throw_type_error("callable", rule)
            assert 0, "unreachable" # make annotator happy
        signature = rule.signature        
        if self.get_builtin(signature):
            error.throw_permission_error(
                "modify", "static_procedure", rule.head.get_prolog_signature())

        function = m.current_module.lookup(signature)
        function.add_rule(rule, end)
        if old_modname is not None:
            self.switch_module(old_modname)

    @jit.elidable_promote('all')
    def get_builtin(self, signature):
        from prolog import builtin # for the side-effects
        return signature.get_extra("builtin")


    # _____________________________________________________
    # parsing-related functionality

    def _build_and_run(self, tree):
        assert self is not None # for the annotator (!)
        from prolog.interpreter.parsing import TermBuilder
        builder = TermBuilder()
        term = builder.build_query(tree)
        if isinstance(term, Callable) and term.signature().eq(callsig):
            self.run(term.argument_at(0), self.modulewrapper.current_module)
        else:
            self._term_expand(term)
        return self.parser

    def _term_expand(self, term):
        if self.modulewrapper.system is not None:
            v = BindingVar()
            call = Callable.build("term_expand", [term, v])
            try:
                self.run(call, self.modulewrapper.current_module)
            except error.UnificationFailed:
                v = BindingVar()
                call = Callable.build("term_expand", [term, v])
                self.run(call, self.modulewrapper.system)
            term = v.dereference(None)
        self.add_rule(term)

    def runstring(self, s):
        from prolog.interpreter.parsing import parse_file
        trees = parse_file(s, self.parser, Engine._build_and_run, self)

    def parse(self, s):
        from prolog.interpreter.parsing import parse_file, TermBuilder
        builder = TermBuilder()
        trees = parse_file(s, self.parser)
        terms = builder.build_many(trees)
        return terms, builder.varname_to_var

    def getoperations(self):
        from prolog.interpreter.parsing import default_operations
        if self.operations is None:
            return default_operations
        return self.operations

    # _____________________________________________________
    # Prolog execution

    def run_query(self, query, module, continuation=None):
        assert isinstance(module, Module)
        fcont = DoneFailureContinuation(self)
        if continuation is None:
            continuation = CutScopeNotifier(self, DoneSuccessContinuation(self), fcont)
        driver(*self.call(query, module, continuation, fcont, Heap()))
    run = run_query

    def call(self, query, module, scont, fcont, heap):
        if isinstance(query, Var):
            query = query.dereference(heap)
        if not isinstance(query, Callable):
            if isinstance(query, Var):
                raise error.throw_instantiation_error()
            raise error.throw_type_error('callable', query)
        signature = query.signature()        
        builtin = self.get_builtin(signature)
        if builtin is not None:
            return BuiltinContinuation(self, module, scont, builtin, query), fcont, heap

        # do a real call
        function = self._get_function(signature, module, query)
        query = function.add_meta_prefixes(query, module.nameatom)
        startrulechain = jit.hint(function.rulechain, promote=True)
        rulechain = startrulechain.find_applicable_rule(query)
        if rulechain is None:
            raise error.UnificationFailed
        scont, fcont, heap = _make_rule_conts(self, scont, fcont, heap, query, rulechain)
        return scont, fcont, heap

    def _get_function(self, signature, module, query): 
        function = module.lookup(signature)
        if function.rulechain is None and self.modulewrapper.system is not None:
            function = self.modulewrapper.system.lookup(signature)
        if function.rulechain is None:
            return error.throw_existence_error(
                    "procedure", query.get_prolog_signature())
        return function

    # _____________________________________________________
    # module handling

    def switch_module(self, modulename):
        m = self.modulewrapper
        try:
            m.current_module = m.modules[modulename]
        except KeyError:
            module = Module(modulename)
            m.modules[modulename] = module
            m.current_module = module

    # _____________________________________________________
    # error handling

    @jit.unroll_safe
    def throw(self, exc, scont, fcont, heap):
        from prolog.interpreter import memo
        # copy to make sure that variables in the exception that are
        # backtracked by the revert_upto below have the right value.
        exc = exc.copy(heap, memo.CopyMemo())
        while not scont.is_done():
            if not isinstance(scont, CatchingDelimiter):
                scont = scont.nextcont
                continue
            discard_heap = scont.heap
            heap = heap.revert_upto(discard_heap)
            try:
                scont.catcher.unify(exc, heap)
            except error.UnificationFailed:
                scont = scont.nextcont
            else:
                return self.call(
                    scont.recover, scont.module, scont.nextcont, scont.fcont, heap)
        raise error.UncaughtError(exc)



    def __freeze__(self):
        return True

def _make_rule_conts(engine, scont, fcont, heap, query, rulechain):
    rule = jit.hint(rulechain, promote=True)
    if rule.contains_cut:
        scont = CutScopeNotifier.insert_scope_notifier(
                engine, scont, fcont)
    restchain = rule.find_next_applicable_rule(query)
    if restchain is not None:
        fcont = UserCallContinuation(engine, scont, fcont, heap, query, restchain)
        heap = heap.branch()

    scont = RuleContinuation(engine, scont, rule, query)
    return scont, fcont, heap

# ___________________________________________________________________
# Continuation classes

def _dot(self, seen):
    if self in seen:
        return
    seen.add(self)
    yield '%s [label="%s", shape=box]' % (id(self), repr(self)[:50])
    for key, value in self.__dict__.iteritems():
        if hasattr(value, "_dot"):
            yield "%s -> %s [label=%s]" % (id(self), id(value), key)
            for line in value._dot(seen):
                yield line


class Continuation(object):
    """ Represents a continuation of the Prolog computation. This can be seen
    as an RPython-compatible way to express closures. """

    def __init__(self, engine, nextcont):
        self.engine = engine
        self.nextcont = nextcont

    def activate(self, fcont, heap):
        """ Follow the continuation. heap is the heap that should be used while
        doing so, fcont the failure continuation that should be activated in
        case this continuation fails. This method can only be called once, i.e.
        it can destruct this object. 
        
        The method should return a triple (next cont, failure cont, heap)"""
        raise NotImplementedError("abstract base class")

    def is_done(self):
        return False

    def find_end_of_cut(self):
        return self.nextcont.find_end_of_cut()

    _dot = _dot

class ContinuationWithModule(Continuation):
    """ This class represents continuations which need
    to take care of the module system. """

    def __init__(self, engine, module, nextcont):
        Continuation.__init__(self, engine, nextcont)
        self.module = module

def view(*objects, **names):
    from dotviewer import graphclient
    content = ["digraph G{"]
    seen = set()
    for obj in list(objects) + names.values():
        content.extend(obj._dot(seen))
    for key, value in names.items():
        content.append("%s -> %s" % (key, id(value)))
    content.append("}")
    p = py.test.ensuretemp("prolog").join("temp.dot")
    p.write("\n".join(content))
    graphclient.display_dot_file(str(p))


class FailureContinuation(object):
    """ A continuation that can represent failures. It has a .fail method that
    is called to figure out what should happen on a failure.
    """
    def __init__(self, engine, nextcont, orig_fcont, heap):
        self.engine = engine
        self.nextcont = nextcont
        self.orig_fcont = orig_fcont
        self.undoheap = heap

    def fail(self, heap):
        """ Needs to be called to get the new success continuation.
        Returns a tuple (next cont, failure cont, heap)
        """
        raise NotImplementedError("abstract base class")

    def cut(self, upto, heap):
        """ Cut away choice points till upto. """
        if self is upto:
            return
        heap = self.undoheap.discard(heap)
        self.orig_fcont.cut(upto, heap)

    def is_done(self):
        return False

    _dot = _dot

def make_failure_continuation(make_func):
    class C(FailureContinuation):
        def __init__(self, engine, scont, fcont, heap, *state):
            FailureContinuation.__init__(self, engine, scont, fcont, heap)
            self.state = state

        def fail(self, heap):
            heap = heap.revert_upto(self.undoheap, discard_choicepoint=True)
            return make_func(C, self.engine, self.nextcont, self.orig_fcont,
                             heap, *self.state)
    C.__name__ = make_func.__name__ + "FailureContinuation"
    def make_func_wrapper(*args):
        return make_func(C, *args)
    make_func_wrapper.__name__ = make_func.__name__ + "_wrapper"
    return make_func_wrapper

class DoneSuccessContinuation(Continuation):
    def __init__(self, engine):
        Continuation.__init__(self, engine, None)
        self.failed = False

    def is_done(self):
        return True

class DoneFailureContinuation(FailureContinuation):
    def __init__(self, engine):
        FailureContinuation.__init__(self, engine, None, None, None)

    def fail(self, heap):
        scont = DoneSuccessContinuation(self.engine)
        scont.failed = True
        return scont, self, heap

    def is_done(self):
        return True


class BodyContinuation(ContinuationWithModule):
    """ Represents a bit of Prolog code that is still to be called. """
    def __init__(self, engine, module, nextcont, body):
        ContinuationWithModule.__init__(self, engine, module, nextcont)
        self.body = body

    def activate(self, fcont, heap):
        return self.engine.call(self.body, self.module, self.nextcont, fcont, heap)

    def __repr__(self):
        return "<BodyContinuation %r>" % (self.body, )

class BuiltinContinuation(ContinuationWithModule):
    """ Represents the call to a builtin. """
    def __init__(self, engine, module, nextcont, builtin, query):
        ContinuationWithModule.__init__(self, engine, module, nextcont)
        self.builtin = builtin
        self.query = query

    def activate(self, fcont, heap):
        return self.builtin.call(self.engine, self.query, self.module, 
                self.nextcont, fcont, heap)

    def __repr__(self):
        return "<BuiltinContinuation %r, %r>" % (self.builtin, self.query, )


class UserCallContinuation(FailureContinuation):
    def __init__(self, engine, nextcont, orig_fcont, heap, query, rulechain):
        FailureContinuation.__init__(self, engine, nextcont, orig_fcont, heap)
        self.query = query
        self.rulechain = rulechain

    def fail(self, heap):
        heap = heap.revert_upto(self.undoheap, discard_choicepoint=True)
        return _make_rule_conts(self.engine, self.nextcont, self.orig_fcont,
                                heap, self.query, self.rulechain)


    def __repr__(self):
        return "<UserCallContinuation query=%r rule=%r>" % (
                self.query, self.rulechain)
    

class RuleContinuation(Continuation):
    """ A Continuation that represents the application of a rule, i.e.:
        - standardizing apart of the rule
        - unifying the rule head with the query
        - calling the body of the rule
    """

    def __init__(self, engine, nextcont, rule, query):
        Continuation.__init__(self, engine, nextcont)
        self._rule = rule
        self.query = query

    def activate(self, fcont, heap):
        nextcont = self.nextcont
        rule = jit.hint(self._rule, promote=True)
        nextcall = rule.clone_and_unify_head(heap, self.query)
        if nextcall is not None:
            return self.engine.call(nextcall, self._rule.module, nextcont, fcont, heap)
        else:
            cont = nextcont
        return cont, fcont, heap

    def __repr__(self):
        return "<RuleContinuation rule=%r query=%r>" % (self._rule, self.query)

class CutScopeNotifier(Continuation):
    def __init__(self, engine, nextcont, fcont_after_cut):
        Continuation.__init__(self, engine, nextcont)
        self.fcont_after_cut = fcont_after_cut

    @staticmethod
    def insert_scope_notifier(engine, nextcont, fcont):
        if isinstance(nextcont, CutScopeNotifier) and nextcont.fcont_after_cut is fcont:
            return nextcont
        return CutScopeNotifier(engine, nextcont, fcont)

    def find_end_of_cut(self):
        return self.fcont_after_cut

    def activate(self, fcont, heap):
        return self.nextcont, fcont, heap


class CatchingDelimiter(ContinuationWithModule):
    def __init__(self, engine, module, nextcont, fcont, catcher, recover, heap):
        ContinuationWithModule.__init__(self, engine, module, nextcont)
        self.catcher = catcher
        self.recover = recover
        self.fcont = fcont
        self.heap = heap

    def activate(self, fcont, heap):
        return self.nextcont, fcont, heap

    def __repr__(self):
        return "<CatchingDelimiter catcher=%s recover=%s>" % (self.catcher, self.recover)
