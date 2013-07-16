from unipycation import *

class Engine2(object):
    """ A wrapper around unipycation.Engine. Hack XXX """
    def __init__(self, db_str):
        self.engine = Engine(db_str)
        self.db = Database(self)
        self.multisol = False
    
    def query_single(self, t, vs):
        return self.engine.query_single(t, vs)

    def query_iter(self, t, vs):
        return self.engine.query_iter(t, vs)

class Database(object):
    """ A class that represents the predicates exposed by a prolog engine """

    def __init__(self, engine):
        self.engine = engine

    def __getattr__(self, name):
        """ Predicates are called by db.name and are resolved dynamically """
        return lambda *args : self._query(name, *args)

    def _query(self, name, *args):
        print(72 * "-")
        print("query %s: %s" % (name, args, ))

        vs = []
        term_args = []
        for i in range(len(args)):
            if args[i] == None:
                e = Var()
                vs.append(e)
            else:
                e = args[i]

            term_args.append(e)

        print("XXX: %s" % term_args)
        t = Term(name, term_args)

        if self.engine.multisol:
            raise NotImplementedError("XXX")
        else:
            sol = self.engine.query_single(t, vs)
            return tuple([ sol[v] for v in vs ])

if __name__ == "__main__":
    e = Engine("f(1, 2, 3).")
    d = Database(e)
    sol = d.f(1, None, None)
    print(sol)
