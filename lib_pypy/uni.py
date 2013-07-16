from unipycation import *

class Engine2(object):
    """ A wrapper around unipycation.Engine. Hack XXX """
    def __init__(self, db_str):
        self.engine = Engine(db_str)
        self.db = Database(self)
        self.multisol = False

class Predicate(object):
    """ Represents a "callable" prolog predicate """

    def __init__(self, engine, name):
        self.engine = engine
        self.multiple_solutions = False
        self.name = name

    def __call__(self, *args):
        filter = lambda e : Var() if e is None else e
        term_args = [ filter(e) for e in args ]
        vs = [ e for e in term_args if type(e) == Var ]
        t = Term(self.name, term_args)

        if self.multiple_solutions:
            raise NotImplementedError("XXX")
        else:
            sol = self.engine.engine.query_single(t, vs)
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
