from pypy.lang.prolog.interpreter.term import Var, Term, Rule, Atom, debug_print, \
    Callable
from pypy.lang.prolog.interpreter.error import UnificationFailed, FunctionNotFound, \
    CutException
from pypy.lang.prolog.interpreter import error

DEBUG = True

class Continuation(object):
    def call(self, engine):
        pass

DONOTHING = Continuation()

class LimitedScopeContinuation(Continuation):
    def __init__(self, continuation):
        self.scope_active = True
        self.continuation = continuation

    def call(self, engine):
        self.scope_active = False
        return self.continuation.call(engine)

START_NUMBER_OF_VARS = 4096


class Frame(object):
    def __init__(self):
        self.vars = [None] * START_NUMBER_OF_VARS
        self.trail = []
        self.needed_vars = 0
        self.last_branch = 0

    def clear(self, length):
        l = max(START_NUMBER_OF_VARS, length)
        self.vars = [None] * l
        self.needed_vars = length
        self.last_branch = length
        self.trail = []

    def getvar(self, index):
        return self.vars[index]

    def setvar(self, index, val):
        # XXX check if oldval != val
        #     it happens all the time in get_last_var_in_chain_and_val()
        oldval = self.vars[index]
        self.vars[index] = val
        # only trail for variables that have a chance to get restored
        # on the last choice point
        if index < self.last_branch:
            self.trail.append((index, oldval))

    def branch(self):
        old_last_branch = self.last_branch
        self.last_branch = self.needed_vars
        return len(self.trail), self.needed_vars, old_last_branch

    def revert(self, state):
        trails, length, old_last_branch = state
        assert length == self.last_branch
        for i in range(len(self.trail) - 1, trails - 1, -1):
            index, val = self.trail[i]
            if index >= length:
                val = None
            self.vars[index] = val
        for i in range(length, self.needed_vars):
            self.vars[i] = None
        del self.trail[trails:]
        self.needed_vars = length

    def discard(self, state):
        old_last_branch = state[2]
        self.last_branch = old_last_branch

    def extend(self, numvars):
        if numvars:
            self.needed_vars += numvars
            newvars = max(0, numvars - (len(self.vars) - self.needed_vars))
            if newvars == 0:
                return
            self.vars.extend([None] * (2 * newvars)) # allocate a bit more
            assert self.needed_vars <= len(self.vars)

    def maxvar(self):
        return self.needed_vars

    def newvar(self):
        result = Var(self.maxvar())
        self.extend(1)
        return result

class Engine(object):
    def __init__(self):
        self.frame = Frame()
        self.signature2rules = {}
        self.parser = None
        self.operations = None
    
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
            assert 0, "unreachable" # XXX make annotator happy
        if signature in builtin.builtins:
            error.throw_permission_error(
                "modify", "static_procedure", rule.head.get_prolog_signature())
        # it's important to not update the list in place, because
        # there might be references to it in the stack somewhere
        rules = self.signature2rules.get(signature, [])
        if end:
            self.signature2rules[signature] = rules + [rule]
        else:
            self.signature2rules[signature] = [rule] + rules

    def run(self, query, continuation=DONOTHING):
        if not isinstance(query, Callable):
            error.throw_type_error("callable", query)
        vars = query.get_max_var() + 1
        self.frame.clear(vars)
        try:
            return self.call(query, continuation)
        except CutException, e:
            self.continue_after_cut(e.continuation)

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

    def call(self, query, continuation=DONOTHING):
        assert isinstance(query, Callable)
        from pypy.lang.prolog.builtin import builtins
        if DEBUG:
            debug_print("calling", query)
        signature = query.signature
        # check for builtins
        builtin = builtins.get(signature, None)
        if builtin is not None:
            return builtin(self, query, continuation)
        # do a real call
        return self.user_call(query, continuation)

    def user_call(self, query, continuation):
        #import pdb; pdb.set_trace()
        signature = query.signature
        rules = self.signature2rules.get(signature, None)
        if rules is None:
            error.throw_existence_error(
                "procedure", query.get_prolog_signature())
        unify_hash = query.get_deeper_unify_hash(self.frame)
        rule, i = self.find_applicable_rule(0, rules, query, unify_hash)
        if rule is None:
            # none of the rules apply
            raise UnificationFailed()
        oldstate = self.frame.branch()
        while 1:
            next, i = self.find_applicable_rule(i, rules, query, unify_hash)
            if next is None:
                self.frame.discard(oldstate)
                break
            if rule.contains_cut:
                continuation = LimitedScopeContinuation(continuation)
                try:
                    result = self.try_rule(rule, query, continuation)
                    self.frame.discard(oldstate)
                    return result
                except UnificationFailed:
                    self.frame.revert(oldstate)
                except CutException, e:
                    if continuation.scope_active:
                        return self.continue_after_cut(e.continuation,
                                                       continuation)
                    raise
            else:
                try:
                    result = self.try_rule(rule, query, continuation)
                    self.frame.discard(oldstate)
                    return result
                except UnificationFailed:
                    self.frame.revert(oldstate)
            rule = next
        if rule.contains_cut:
            continuation = LimitedScopeContinuation(continuation)
            try:
                return self.try_rule(rule, query, continuation)
            except CutException, e:
                if continuation.scope_active:
                    self.continue_after_cut(e.continuation, continuation)
                raise
        return self.try_rule(rule, query, continuation)

    def try_rule(self, rule, query, continuation=DONOTHING):
        if DEBUG:
            debug_print("trying rule", rule, query, self.frame.vars[:self.frame.needed_vars])
        try:
            # standardizing apart
            nextcall = rule.clone_and_unify_head(self.frame, query)
        except UnificationFailed:
            if DEBUG:
                debug_print("didn't work", rule, query, self.frame.vars[:self.frame.needed_vars])
            raise
        if DEBUG:
            debug_print("worked", rule, query, self.frame.vars[:self.frame.needed_vars])
        if nextcall is not None:
            return self.call(nextcall, continuation)
        return continuation.call(self)

    def find_applicable_rule(self, startindex, rules, query, uh1):
        i = startindex
        while i < len(rules):
            uh2 = rules[i].unify_hash
            assert len(uh1) == len(uh2)
            for j in range(len(uh1)):
                if uh1[j] != 0 and uh2[j] != 0 and uh1[j] != uh2[j]:
                    break
            else:
                return rules[i], i + 1
            i += 1
        return None, 0

    def continue_after_cut(self, continuation, lsc=None):
        while 1:
            try:
                return continuation.call(self)
            except CutException, e:
                if lsc is not None and not lsc.scope_active:
                    raise
                continuation = e.continuation

    def parse(self, s):
        from pypy.lang.prolog.interpreter.parsing import parse_file, TermBuilder, lexer
        builder = TermBuilder()
        trees = parse_file(s, self.parser)
        terms = builder.build_many(trees)
        return terms, builder.var_to_pos

    def getoperations(self):
        from pypy.lang.prolog.interpreter.parsing import default_operations
        if self.operations is None:
            return default_operations
        return self.operations
