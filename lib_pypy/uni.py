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
        name = self.name
        print("query %s: %s" % (name, args, ))

        vs = []
        term_args = []
        for i in range(len(args)):
            if args[i] is None:
                e = Var()
                vs.append(e)
            else:
                e = args[i]

            term_args.append(e)

        t = Term(name, term_args)

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
        return Predicate(self.engine, name)

if __name__ == "__main__":
    e = Engine2("f(1, 2, 3).")
    d = Database(e)
    sol = d.f(1, None, None)
    print(sol)
