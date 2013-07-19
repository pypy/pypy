from unipycation import *

def build_prolog_list(elems):
    """ Converts a Python list into a cons chain """
    #if len(elems) == 0:
    #    return "[]"
    #else:
    #    return Term(".", [ elems[0], build_prolog_list(elems[1:]) ])

    # Iterative, to avoid list slicing (linear in list size)
    n_elems = len(elems)
    e = "[]"
    for i in xrange(n_elems - 1, -1, -1):
        e = Term(".", [elems[i], e])

    return e

class Engine(object):
    """ A wrapper around unipycation.CoreEngine. """
    def __init__(self, db_str):
        self.engine = CoreEngine(db_str)
        self.db = Database(self)
        self.terms = TermPool()
        self.many_solutions = False

class SolutionIterator(object):
    """ A wrapper around unipycation.CoreSolutionIterator. """
    def __init__(self, iter, vs):
        self.iter = iter
        self.vars = vs # indicates order of returned solutions

    def __iter__(self): return self

    def next(self):
        sol = self.iter.next()
        return tuple([ sol[v] for v in self.vars ])

class Predicate(object):
    """ Represents a "callable" prolog predicate """

    def __init__(self, engine, name):
        self.engine = engine
        self.many_solutions = False
        self.name = name

    @staticmethod
    def _arg_filter(e):
        if e is None:
            return Var()
        elif isinstance(e, list):
            return build_prolog_list(e)
        else:
            return e

    @staticmethod
    def _back_to_py(e):
        if e == "[]":
            return []
        if (not isinstance(e, Term)):
            return e
        elif e.name == ".":
            assert len(e) == 2
            return [ Predicate._back_to_py(e.args[0]) ] + \
                    Predicate._back_to_py(e.args[1])
        else:
            assert(False) # should not happen

    def __call__(self, *args):
        term_args = [ Predicate._arg_filter(e) for e in args ]

        vs = [ e for e in term_args if type(e) == Var ]
        t = Term(self.name, term_args)

        if self.many_solutions:
            it = self.engine.engine.query_iter(t, vs)
            return SolutionIterator(it, vs)
        else:
            sol = self.engine.engine.query_single(t, vs)

            if sol is None:
                return None # contradiction
            else:
                return tuple([ Predicate._back_to_py(sol[v]) for v in vs ])
    
class Database(object):
    """ A class that represents the predicates exposed by a prolog engine """

    def __init__(self, engine):
        self.engine = engine

    def __getattr__(self, name):
        """ Predicates are called by db.name and are resolved dynamically """
        pred = Predicate(self.engine, name)
        setattr(self, name, pred)
        return pred

class TermPool(object):
    """ Represents the term pool, some magic to make term creation prettier """

    @staticmethod
    def _magic_convert(name, args):
        """ For now this is where pylists become cons chains in term args """

        new_args = []
        for a in args:
            if isinstance(a, list):
                new_args.append(build_prolog_list(a))
            else:
                new_args.append(a)

        return Term(name, new_args)

    def __getattr__(self, name):
        # Note that we cant memoise these due to the args being variable
        return lambda *args : TermPool._magic_convert(name, args)
