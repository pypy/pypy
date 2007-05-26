from pypy.jit.hintannotator.policy import ManualGraphPolicy
from pypy.lang.prolog.interpreter import term, engine, helper
from pypy.translator.translator import graphof
from pypy.annotation.specialize import getuniquenondirectgraph


forbidden_modules = {'pypy.lang.prolog.interpreter.parser': True,
                     }

good_modules = {'pypy.lang.prolog.builtin.control': True,
                'pypy.lang.prolog.builtin.register': True
               }


PORTAL = engine.Engine.portal_try_rule.im_func

class PyrologHintAnnotatorPolicy(ManualGraphPolicy):
    PORTAL = PORTAL
    def look_inside_graph_of_module(self, graph, func, mod):
        if mod in forbidden_modules:
            return False
        if mod in good_modules:
            return True
        if mod.startswith("pypy.lang.prolog"):
            return False
        return True

    def fill_timeshift_graphs(self, portal_graph):
        import pypy
        for cls in [term.Var, term.Term, term.Number, term.Atom]:
            self.seegraph(cls.copy)
            self.seegraph(cls.__init__)
            self.seegraph(cls.copy_and_unify)
        for cls in [term.Term, term.Number, term.Atom]:
            self.seegraph(cls.copy_and_basic_unify)
            self.seegraph(cls.dereference)
            self.seegraph(cls.copy_and_basic_unify)
        for cls in [term.Var, term.Term, term.Number, term.Atom]:
            self.seegraph(cls.get_unify_hash)
            self.seegraph(cls.eval_arithmetic)
        for cls in [term.Callable, term.Atom, term.Term]:
            self.seegraph(cls.get_prolog_signature)
            self.seegraph(cls.unify_hash_of_children)
        self.seegraph(PORTAL)
        self.seegraph(engine.Heap.newvar)
        self.seegraph(term.Rule.clone_and_unify_head)
        self.seegraph(engine.Engine.call)
        self.seegraph(engine.Engine._call)
        self.seegraph(engine.Engine.user_call)
        self.seegraph(engine.Engine._user_call)
        self.seegraph(engine.Engine.try_rule)
        self.seegraph(engine.Engine._try_rule)
        self.seegraph(engine.Engine.main_loop)
        self.seegraph(engine.Engine.dispatch_bytecode)
        self.seegraph(engine.LinkedRules.find_applicable_rule)
        for method in "branch revert discard newvar extend maxvar".split():
            self.seegraph(getattr(engine.Heap, method))
        self.seegraph(engine.Continuation.call)
        for cls in [engine.Continuation, engine.LimitedScopeContinuation,
                    pypy.lang.prolog.builtin.control.AndContinuation]:
            self.seegraph(cls._call)
        for function in "".split():
            self.seegraph(getattr(helper, function))

def get_portal(drv):
    t = drv.translator
    portal = getattr(PORTAL, 'im_func', PORTAL)

    policy = PyrologHintAnnotatorPolicy()
    policy.seetranslator(t)
    return portal, policy
