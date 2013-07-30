from unipycation import Term, Var, CoreEngine, PrologError

class InstantiationError(Exception): pass

def build_prolog_list(elems):
    """ Converts a Python list into a cons chain """
    # Iterative, to avoid list slicing (linear in list size)
    n_elems = len(elems)
    e = "[]"
    for i in xrange(n_elems - 1, -1, -1):
        e = Term(".", [elems[i], e])

    return e

def unpack_prolog_list(obj):
    assert obj.name == "."
    curr = obj
    result = []
    while True:
        if isinstance(curr, Var): # the rest of the list is unknown
            raise InstantiationError("The tail of a list was undefined")
        if curr == "[]": # end of list
            return result
        if not isinstance(curr, Term) or not curr.name == ".":
            return obj # malformed list, just return it unconverted
        result.append(curr.args[0])
        curr = curr.args[1]

class Engine(object):
    """ A wrapper around unipycation.CoreEngine. """
    def __init__(self, db_str):
        self.engine = CoreEngine(db_str)
        self.db = Database(self)
        self.terms = TermPool()

class SolutionIterator(object):
    """ A wrapper around unipycation.CoreSolutionIterator. """
    def __init__(self, it, vs):
        self.it = it
        self.vs = vs # indicates order of returned solutions

    def __iter__(self): return self

    def next(self):
        sol = self.it.next()
        return Predicate._make_result_tuple(sol, self.vs)

class Predicate(object):
    """ Represents a "callable" prolog predicate """

    def __init__(self, engine, name):
        self.engine = engine
        self.many_solutions = False
        self.name = name

    @staticmethod
    def _convert_to_prolog(e):
        if isinstance(e, list):
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
            return unpack_prolog_list(e)
        else:
            # is a Term
            return e

    @staticmethod
    def _make_result_tuple(sol, variables):
        return tuple(unrolling_map(lambda v: sol[v], variables))

    def __call__(self, *args):
        vs = []
        def _convert_arg(e):
            if e is None:
                var = Var()
                vs.append(var)
                return var
            return self._convert_to_prolog(e)
        term_args = unrolling_map(_convert_arg, args)
        t = Term(self.name, term_args)

        if self.many_solutions:
            it = self.engine.engine.query_iter(t, vs)
            return SolutionIterator(it, vs)
        else:
            sol = self.engine.engine.query_single(t, vs)

            if sol is None:
                return None # contradiction
            else:
                return Predicate._make_result_tuple(sol, vs)
    
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

        new_args = unrolling_map(Predicate._convert_to_prolog(a))
        return Term(name, new_args)

    def __getattr__(self, name):
        # Note that we cant memoise these due to the args being variable
        return lambda *args : TermPool._magic_convert(name, args)


def unrolling_map(fun, sequence):
    """ This function behaves like a simple version of map, taking a function
    of one argument, and a sequence. The added complication over map is that it
    will unroll the loop for small lists. The benefit is that for the short
    cases, the JIT does not see the loop and thus the construction of the
    result is completely transparent to it. """
    length = len(sequence)
    if length == 0:
        return []
    elif length == 1:
        return [fun(sequence[0])]
    elif length == 2:
        return [fun(sequence[0]), fun(sequence[1])]
    elif length == 3:
        return [fun(sequence[0]), fun(sequence[1]), fun(sequence[2])]
    elif length == 4:
        return [fun(sequence[0]), fun(sequence[1]), fun(sequence[2]),
                fun(sequence[3])]
    elif length == 5:
        return [fun(sequence[0]), fun(sequence[1]), fun(sequence[2]),
                fun(sequence[3]), fun(sequence[4])]
    return map(fun, sequence)
