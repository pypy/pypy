from unipycation import *

class Engine(object):
    """ A wrapper around unipycation.CoreEngine. """
    def __init__(self, db_str):
        self.engine = CoreEngine(db_str)
        self.db = Database(self)
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

    def __call__(self, *args):
        filter = lambda e : Var() if e is None else e
        term_args = [ filter(e) for e in args ]
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
                return tuple([ sol[v] for v in vs ])
    
class Database(object):
    """ A class that represents the predicates exposed by a prolog engine """

    def __init__(self, engine):
        self.engine = engine

    def __getattr__(self, name):
        """ Predicates are called by db.name and are resolved dynamically """
        pred = Predicate(self.engine, name)
        setattr(self, name, pred)
        return pred
