from pypy.lang.prolog.interpreter.term import Var, Term, Rule, Atom, debug_print, \
    Callable
from pypy.lang.prolog.interpreter.error import UnificationFailed, FunctionNotFound, \
    CutException
from pypy.lang.prolog.interpreter import error
from pypy.rlib.jit import hint, we_are_jitted, _is_early_constant, purefunction
from pypy.rlib.objectmodel import specialize
from pypy.rlib.unroll import unrolling_iterable

DEBUG = False

# bytecodes:
CALL = 'a'
USER_CALL = 'u'
TRY_RULE = 't'
CONTINUATION = 'c'
DONE = 'd'


class Continuation(object):
    def call(self, engine, choice_point=True):
        if choice_point:
            return engine.main_loop(CONTINUATION, None, self, None)
        return (CONTINUATION, None, self, None)

    def _call(self, engine):
        return (DONE, None, None, None)

DONOTHING = Continuation()

class LimitedScopeContinuation(Continuation):
    def __init__(self, continuation):
        self.scope_active = True
        self.continuation = continuation

    def _call(self, engine):
        self.scope_active = False
        return self.continuation.call(engine, choice_point=False)

class Heap(object):
    def __init__(self):
        self.trail = []

    def reset(self):
        self.trail = []
        self.last_branch = 0

    def add_trail(self, var):
        self.trail.append((var, var.binding))

    def branch(self):
        return len(self.trail)

    def revert(self, state):
        trails = state
        for i in range(len(self.trail) - 1, trails - 1, -1):
            var, val = self.trail[i]
            var.binding = val
        del self.trail[trails:]

    def discard(self, state):
        pass #XXX for now

    def maxvar(self):
        XXX
        return self.needed_vars

    def newvar(self):
        result = Var(self)
        return result

class LinkedRules(object):
    _immutable_ = True
    def __init__(self, rule, next=None):
        self.rule = rule
        self.next = next

    def copy(self, stopat=None):
        first = LinkedRules(self.rule)
        curr = self.next
        copy = first
        while curr is not stopat:
            new = LinkedRules(curr.rule)
            copy.next = new
            copy = new
            curr = curr.next
        return first, copy

    def find_applicable_rule(self, uh2):
        #import pdb;pdb.set_trace()
        while self:
            uh = self.rule.unify_hash
            hint(uh, concrete=True)
            uh = hint(uh, deepfreeze=True)
            j = 0
            while j < len(uh):
                hint(j, concrete=True)
                hash1 = uh[j]
                hash2 = uh2[j]
                if hash1 != 0 and hash2 * (hash2 - hash1) != 0:
                    break
                j += 1
            else:
                return self
            self = self.next
        return None

    def __repr__(self):
        return "LinkedRules(%r, %r)" % (self.rule, self.next)



class Function(object):
    def __init__(self, firstrule=None):
        if firstrule is None:
            self.rulechain = self.last = None
        else:
            self.rulechain = LinkedRules(firstrule)
            self.last = self.rulechain

    def add_rule(self, rule, end):
        if self.rulechain is None:
            self.rulechain = self.last = LinkedRules(rule)
        elif end:
            self.rulechain, last = self.rulechain.copy()
            self.last = LinkedRules(rule)
            last.next = self.last
        else:
            self.rulechain = LinkedRules(rule, self.rulechain)

    def remove(self, rulechain):
        self.rulechain, last = self.rulechain.copy(rulechain)
        last.next = rulechain.next


class Engine(object):
    def __init__(self):
        self.heap = Heap()
        self.signature2function = {}
        self.parser = None
        self.operations = None
        #XXX circular imports hack
        from pypy.lang.prolog.builtin import builtins_list
        globals()['unrolling_builtins'] = unrolling_iterable(builtins_list) 

    def add_rule(self, rule, end=True):
        from pypy.lang.prolog import builtin
        if DEBUG:
            debug_print("add_rule", rule)
        if isinstance(rule, Term):
            if rule.name == ":-":
                rule = Rule(rule.args[0], rule.args[1])
            else:
                rule = Rule(rule, None)
            signature = rule.signature
        elif isinstance(rule, Atom):
            rule = Rule(rule, None)
            signature = rule.signature
        else:
            error.throw_type_error("callable", rule)
            assert 0, "unreachable" # make annotator happy
        if signature in builtin.builtins:
            error.throw_permission_error(
                "modify", "static_procedure", rule.head.get_prolog_signature())
        function = self.signature2function.get(signature, None)
        if function is not None:
            self.signature2function[signature].add_rule(rule, end)
        else:
            self.signature2function[signature] = Function(rule)

    def run(self, query, continuation=DONOTHING):
        if not isinstance(query, Callable):
            error.throw_type_error("callable", query)
        try:
            return self.call(query, continuation, choice_point=True)
        except CutException, e:
            return self.continue_after_cut(e.continuation)

    def _build_and_run(self, tree):
        from pypy.lang.prolog.interpreter.parsing import TermBuilder
        builder = TermBuilder()
        term = builder.build_query(tree)
        if isinstance(term, Term) and term.name == ":-" and len(term.args) == 1:
            self.run(term.args[0])
        else:
            self.add_rule(term)
        return self.parser

    def runstring(self, s):
        from pypy.lang.prolog.interpreter.parsing import parse_file
        trees = parse_file(s, self.parser, Engine._build_and_run, self)

    def call(self, query, continuation=DONOTHING, choice_point=True):
        assert isinstance(query, Callable)
        if not choice_point:
            return (CALL, query, continuation, None)
        return self.main_loop(CALL, query, continuation)

    def _call(self, query, continuation):
        signature = query.signature
        from pypy.lang.prolog.builtin import builtins
        builtins = hint(builtins, deepfreeze=True)
        signature = hint(signature, promote=True)
        for bsig, builtin in unrolling_builtins:
            if signature == bsig:
                return builtin.call(self, query, continuation)
        return self.user_call(query, continuation, choice_point=False)

    def _opaque_call(self, query, continuation):
        from pypy.lang.prolog.builtin import builtins
        signature = query.signature
        builtin = builtins.get(signature, None)
        if builtin is not None:
            return builtin.call(self, query, continuation)
        # do a real call
        return self.user_call(query, continuation, choice_point=False)

    def main_loop(self, where, query, continuation, rule=None):
        next = (DONE, None, None, None)
        hint(where, concrete=True)
        hint(rule, concrete=True)
        while 1:
            if where == DONE:
                return next
            next = self.dispatch_bytecode(where, query, continuation, rule)
            where, query, continuation, rule = next
            where = hint(where, promote=True)

    def dispatch_bytecode(self, where, query, continuation, rule):
        if where == CALL:
            next = self._call(query, continuation)
        elif where == TRY_RULE:
            rule = hint(rule, promote=True)
            next = self._try_rule(rule, query, continuation)
        elif where == USER_CALL:
            next = self._user_call(query, continuation)
        elif where == CONTINUATION:
            hint(continuation.__class__, promote=True)
            next = continuation._call(self)
        else:
            raise Exception("unknown bytecode")
        return next

    @purefunction
    def _jit_lookup(self, signature):
        signature2function = self.signature2function
        function = signature2function.get(signature, None)
        if function is None:
            signature2function[signature] = function = Function()
        return function

    def user_call(self, query, continuation, choice_point=True):
        if not choice_point:
            return (USER_CALL, query, continuation, None)
        return self.main_loop(USER_CALL, query, continuation)

    def _user_call(self, query, continuation):
        signature = hint(query.signature, promote=True)
        function = self._jit_lookup(signature)
        startrulechain = function.rulechain
        startrulechain = hint(startrulechain, promote=True)
        if startrulechain is None:
            error.throw_existence_error(
                "procedure", query.get_prolog_signature())

        unify_hash = query.unify_hash_of_children(self.heap)
        rulechain = startrulechain.find_applicable_rule(unify_hash)
        if rulechain is None:
            # none of the rules apply
            raise UnificationFailed()
        rule = rulechain.rule
        rulechain = rulechain.next
        oldstate = self.heap.branch()
        while 1:
            if rulechain is not None:
                rulechain = rulechain.find_applicable_rule(unify_hash)
                choice_point = rulechain is not None
            else:
                choice_point = False
            hint(rule, concrete=True)
            if rule.contains_cut:
                continuation = LimitedScopeContinuation(continuation)
                try:
                    result = self.try_rule(rule, query, continuation)
                    self.heap.discard(oldstate)
                    return result
                except UnificationFailed:
                    self.heap.revert(oldstate)
                except CutException, e:
                    if continuation.scope_active:
                        return self.continue_after_cut(e.continuation,
                                                       continuation)
                    raise
            else:
                inline = rule.body is None # inline facts
                try:
                    # for the last rule (rulechain is None), this will always
                    # return, because choice_point is False
                    result = self.try_rule(rule, query, continuation,
                                           choice_point=choice_point,
                                           inline=inline)
                    self.heap.discard(oldstate)
                    return result
                except UnificationFailed:
                    assert choice_point
                    self.heap.revert(oldstate)
            rule = rulechain.rule
            rulechain = rulechain.next

    def try_rule(self, rule, query, continuation=DONOTHING, choice_point=True,
                 inline=False):
        if not choice_point:
            return (TRY_RULE, query, continuation, rule)
        if not we_are_jitted():
            return self.portal_try_rule(rule, query, continuation, choice_point)
        if inline:
            return self.main_loop(TRY_RULE, query, continuation, rule)
        #if _is_early_constant(rule):
        #    rule = hint(rule, promote=True)
        #    return self.portal_try_rule(rule, query, continuation, choice_point)
        return self._opaque_try_rule(rule, query, continuation, choice_point)

    def _opaque_try_rule(self, rule, query, continuation, choice_point):
        return self.portal_try_rule(rule, query, continuation, choice_point)

    def portal_try_rule(self, rule, query, continuation, choice_point):
        hint(None, global_merge_point=True)
        hint(choice_point, concrete=True)
        if not choice_point:
            return self._try_rule(rule, query, continuation)
        where = TRY_RULE
        next = (DONE, None, None, None)
        hint(where, concrete=True)
        hint(rule, concrete=True)
        signature = hint(query.signature, promote=True)
        while 1:
            hint(None, global_merge_point=True)
            if where == DONE:
                return next
            if rule is not None:
                assert rule.signature == signature
            next = self.dispatch_bytecode(where, query, continuation, rule)
            where, query, continuation, rule = next
            rule = hint(rule, promote=True)
            if query is not None:
                signature = hint(query.signature, promote=True)
            where = hint(where, promote=True)

    def _try_rule(self, rule, query, continuation):
        rule = hint(rule, deepfreeze=True)
        hint(self, concrete=True)
        # standardizing apart
        nextcall = rule.clone_and_unify_head(self.heap, query)
        if nextcall is not None:
            return self.call(nextcall, continuation, choice_point=False)
        else:
            return continuation.call(self, choice_point=False)

    def continue_after_cut(self, continuation, lsc=None):
        while 1:
            try:
                return continuation.call(self, choice_point=True)
            except CutException, e:
                if lsc is not None and not lsc.scope_active:
                    raise
                continuation = e.continuation

    def parse(self, s):
        from pypy.lang.prolog.interpreter.parsing import parse_file, TermBuilder, lexer
        builder = TermBuilder()
        trees = parse_file(s, self.parser)
        terms = builder.build_many(trees)
        return terms, builder.varname_to_var

    def getoperations(self):
        from pypy.lang.prolog.interpreter.parsing import default_operations
        if self.operations is None:
            return default_operations
        return self.operations




