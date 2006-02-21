import threading

from constraint import FiniteDomain


#----------- Exceptions ---------------------------------
class VariableException(Exception):
    def __init__(self, name):
        self.name = name

class AlreadyInStore(VariableException):
    def __str__(self):
        return "%s already in store" % self.name

class NotAVariable(VariableException):
    def __str__(self):
        return "%s is not a variable" % self.name

#----------- Variables ----------------------------------
class EqSet(set):
    """An equivalence set for variables"""

##     def __str__(self):
##         if len(self) == 0:
##             return ''
##         for var in self:
##             '='.join(var.name)

class NoValue:
    pass

class Var(object):
    """Single-assignment variable"""

    def __init__(self, name, cs):
        if name in cs.names:
            raise AlreadyInStore(name)
        self.name = name
        # the creation-time (top-level) space
        self._cs = cs
        # top-level 'commited' binding
        self._val = NoValue
        # domains in multiple spaces
        # self._doms = {cs : FiniteDomain([])}
        # when updated while unification happens, keep track
        # of our initial value (for failure cases)
        self._previous = None
        self._changed = False
        # a condition variable for concurrent access
        self._value_condition = threading.Condition()

    # for consumption by the global cs

    def _is_bound(self):
        return not isinstance(self._val, EqSet) \
               and self._val != NoValue

    # atomic unification support

    def _commit(self):
        self._changed = False

    def _abort(self):
        self.val = self._previous
        self._changed = False

    # value accessors
    def _set_val(self, val):
        self._value_condition.acquire()
        if self._cs.in_transaction:
            if not self._changed:
                self._previous = self._val
                self._changed = True
        self._val = val
        self._value_condition.notifyAll()
        self._value_condition.release()
        
    def _get_val(self):
        return self._val
    val = property(_get_val, _set_val)

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

    def bind(self, val):
        """top-level space bind"""
        self._cs.bind(self, val)

    is_bound = _is_bound

    #-- domain setter/getter is per space
##     def cs_set_dom(self, cs, dom):
##         self._doms[cs] = dom

##     def cs_get_dom(self, cs):
##         self._doms.setdefault(cs, FiniteDomain([]))
##         return self._doms[cs]

    #-- Dataflow ops with concurrent semantics ------
    # should be used by threads that want to block on
    # unbound variables

    def get(self):
        """Make threads wait on the variable
           being bound in the top-level space
        """
        try:
            self._value_condition.acquire()
            while not self._is_bound():
                self._value_condition.wait()
            return self.val
        finally:
            self._value_condition.release()


#-- stream stuff -----------------------------

class Pair(object):
    """similar to CONS in Lisp"""

    def __init__(self, car, cdr):
        self._car = car
        self._cdr = cdr

    def first(self):
        return self._car

    def set_first(self, first):
        self._cdr = first

    def rest(self):
        return self._cdr

    def set_rest(self, stuff):
        self._cdr = stuff

    def as_tuple(self):
        return (self._car, self._cdr)

    def is_empty(self):
        return self._car is None and self._cdr is None

    def length(self):
        ln = 0
        curr = self
        if curr.first() != None:
            ln += 1
        while curr.rest() != None:
            curr = curr.rest()
            if curr.first() != None:
                ln += 1
            # check for circularity
            if curr == self: return ln
        return ln

    def __str__(self):
        # This will show bogus stuff for trees ...
        seen = set()
        strs = []

        def build_elt_str(elt):
            if elt in seen:
                strs.pop() ; strs.pop()
                # show ellipsis when recursing
                strs.append('...')
            elif isinstance(elt, Pair):
                seen.add(elt)
                build_pair_str(elt)
            else:
                if elt is None:
                    strs.pop()
                elif isinstance(elt, Var):
                    if elt.is_bound():
                        strs.append(str(elt.val))
                    else:
                        strs.append(elt.name)
                else:
                    strs.append(str(elt))

        def build_pair_str(pair):
            build_elt_str(pair._car)
            strs.append('|')
            build_elt_str(pair._cdr)

        if self._car is None:
            return 'nil'
        build_pair_str(self)
        return ''.join(strs)

def make_list(data=None):
    """Builds a list with pairs"""
    assert (data is None) \
           or type(data) in (list, tuple, set)
    if data is None:
        return Pair(None, None)
    curr = Pair(data[0], None)
    head = curr
    for datum in data[1:]:
        curr.set_rest(Pair(datum, None))
        curr = curr.rest()
    return head

class CList(Pair):
    """A List supporting concurrent access"""

    def __init__(self, car, cdr):
        Pair.__init__(self, car, cdr)
        self.last_condition = threading.Condition()

    def set_rest(self, rest):
        self.last_condition.acquire()
        try:
            self._cdr = rest
            self.last_condition.notifyAll()
        finally:
            self.last_condition.release()

    def rest(self):
        self.last_condition.acquire()
        try:
            while self._cdr == None:
                self.condition.wait()
            return self._cdr
        finally:
            self.last_condition.release()
        

class Stream(object):
    """A FIFO stream"""

    def __init__(self, elts=Pair(None, None)):
        self.head = elts
        if elts.first() == None:
            self.tail = elts
        else:
            curr = elts.rest()
            prev = elts
            while isinstance(curr, Pair):
                prev = curr
                curr = curr.rest()
            # last pair of the chain
            self.tail = prev
        # head hurts tail sometimes ...
        self.empty_condition = threading.Condition()

    def get(self):
        print self.head
        # first thing to check is whether
        # there is stuff to feed
        self.empty_condition.acquire()
        try:
            if self.head == self.tail:
                # there might remain one element there
                while self.head.is_empty():
                    self.empty_condition.wait()
            # sky is clear : there is something to get
            elt = self.head.first()
            # we might want to advance to the next pair
            if self.head != self.tail:
                self.head = self.head.rest()
            else:
                # or just nullify what we read
                # to avoid reading it again ...
                self.head._car = None
        finally:
            self.empty_condition.release()
        return elt

    def put(self, val):
        # first, check for emptyness special case
        self.empty_condition.acquire()
        try:
            if self.head.is_empty():
                # then we put stuff into head
                # without consing and just return
                self.head._car = val
                self.empty_condition.notifyAll()
                return
        finally:
            self.empty_condition.release()
        # either we did put and return
        # or nothing done yet
        new_tail = Pair(val, None)
        self.tail.set_rest(new_tail)
        self.tail = new_tail

    def __str__(self):
        return str(self.head)


