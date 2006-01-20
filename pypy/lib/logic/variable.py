#----------- Exceptions ---------------------------------
class VariableException(Exception):
    def __init__(self, name):
        self.name = name

class NotAVariable(VariableException):
    def __str__(self):
        return "%s is not a variable" % self.name

#----------- Variables ----------------------------------
class EqSet(set):
    """An equivalence set for variables"""
    pass

class NoValue:
    pass

class Var(object):

    def __init__(self, name, store):
        self.name = name
        self.store = store
        # top-level 'commited' binding
        self._val = NoValue
        # when updated in a 'transaction', keep track
        # of our initial value (for abort cases)
        self.previous = None
        self.changed = False

    def is_bound(self):
        return not isinstance(self.val, EqSet) \
               and self.val != NoValue

    def commit(self):
        self.changed = False

    def abort(self):
        self.val = self.previous
        self.changed = False

    def set_val(self, val):
        if self.store.in_transaction:
            if not self.changed:
                self.previous = self._val
                self.changed = True
                print "in transaction, %s <- %s" % (self.name, val)
        self._val = val
    def get_val(self):
        return self._val
    val = property(get_val, set_val)

    def __str__(self):
        if self.is_bound():
            return "%s = %s" % (self.name, self.val)
        return "%s" % self.name

    def __repr__(self):
        return self.__str__()

    def __eq__(self, thing):
        return isinstance(thing, Var) \
               and self.name == thing.name

    def __hash__(self):
        return self.name.__hash__()

def var(name):
    v = Var(name, _store)
    _store.add_unbound(v)
    return v


