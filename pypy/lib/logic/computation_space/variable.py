import threading
import time

#----------- Exceptions ---------------------------------
class AlreadyBound(Exception):
    def __init__(self, var, val):
        self.var = var
        self.val = val
    
    def __str__(self):
        var, val = self.var, self.val
        return "can't bind %s to %s" % (var, val)

class UnificationFailure(Exception):
    def __init__(self, var1, var2, cause=None):
        self.var1, self.var2 = (var1, var2)
        self.cause = cause

    def __str__(self):
        diag = "%s %s can't be unified" % \
               (self.var1, self.var2)
        if self.cause:
            diag += " because %s" % self.cause
        return diag

#----------- Variables ----------------------------------
class Eqset(set): pass

class NoValue: pass # kill me !

class NoDom: pass # kill me !

class Var(object):
    """Spaceless dataflow variable"""
    _count_lock = threading.Lock()
    _vcount = 0
    
    def __init__(self, value=None, name=None):
        try:
            Var._count_lock.acquire()
            if name: self.name = name
            else: self.name = str(Var._vcount)
        finally:
            Var._count_lock.release()
        Var._vcount += 1
        if value:
            self._val = value
            self._bound = True
        else:
            self._val = Eqset([self])
            self._bound = False
        # a condition variable for Wait
        self._value_condition = threading.Condition()
        # for WaitNeeded
        self._need_condition = threading.Condition()

    # value accessors
    def _set_val(self, val):
        if self._bound:
            if val != self._val:
                raise AlreadyBound(self, val)
        self._val = val
        self._bound = True
        
    def _get_val(self):
        if self._bound:
            return self._val
        return NoValue

    def __str__(self):
        if self.is_bound():
            return "<%s=%s>" % (self.name, self.val)
        return "<?%s>" % self.name

    def __repr__(self):
        return self.__str__()

    # public interface
    val = property(_get_val, _set_val)

    def is_bound(self):
        return self._bound

    def is_free(self):
        return not self._bound

    def aliases(self):
        if self._bound:
            return Eqset([self])
        return self._val
        
    def bind(self, val):
        self._value_condition.acquire()
        try:
            self._bind(val)
            self._value_condition.notifyAll()
        finally:
            self._value_condition.release()
            
    def wait(self):
        try:
            self._need_condition.acquire()
            self._need_condition.notifyAll()
        finally:
            self._need_condition.release()
        try:
            self._value_condition.acquire()
            while not self.is_bound():
                t1 = time.time()
                self._value_condition.wait(10)
                t2 = time.time()
                if t2-t1>10:
                    raise RuntimeError("possible deadlock on %s" % self)
            return self.val
        finally:
            self._value_condition.release()

    def wait_needed(self):
        try:
            self._need_condition.acquire()
            self._need_condition.wait()
        finally:
            self._need_condition.release()


    #-- the real bind --------------------------------------

    def _bind(self, thing):
        """1. aliasing of unbound variables
           2. assign unbound var to bound var
           3. assign value to self
        """
        if isinstance(thing, Var): 
            if _both_are_bound(self, thing):
                if thing.val == self.val:
                    return 
                raise UnificationFailure(self, thing)
            if self.is_bound(): # 2b. self is bound, not var
                var._assign(self.val)
            elif thing.is_bound(): # 2a.var is bound, not self
                self._assign(thing.val)
            else: # 1. both are unbound
                self._alias(thing)
        else: # 3. thing is really a value
            if self.is_bound():
                if self.val == thing:
                    return 
                raise UnificationFailure(self, thing)
            self._assign(thing)

    def _assign(self, val):
        # bind all aliased vars to val
        # print "assignation : %s <- %s" % (self, val)
        for var in self._val:
            var.val = val

    def _alias(self, var):
        #print "aliasing variables : %s %s" % (self, var)
        eqs = var._val
        if self._val == eqs: return
        # merge two eqsets into one
        neqs = self._val | eqs
        # let's realias everyone
        for var in neqs:
            var._val = neqs

var = Var

#-- UNIFY ------------------------------------------

def unify(x, y):
    #print "unify %s with %s" % (x,y)
    check_and_memoize_pair(x, y)
    if not isinstance(x, Var):
        if not isinstance(y, Var):
            # duh ! x & y not vars
            _unify_values(x, y)
        # x not a var, reverse args. order
        unify(y, x)
    elif not isinstance(y, Var):
        # x is Var, y a value
        x.bind(y)
    # x and y are vars
    elif _both_are_bound(x, y):
        _unify_values(x.val ,y.val)
    elif x.is_bound():
        y.bind(x.val)
    # aliasing x & y
    else:
        x.bind(y)
    reset_memo()

def _unify_values(x, y):
    #print "unify values %s %s" % (x, y)
    if type(x) in [list, set] and isinstance(y, type(x)):
        _unify_iterable(x, y)
    elif type(x) is dict and isinstance(y, type(x)):
        _unify_mapping(x, y)
    else:
        if x != y:
            raise UnificationFailure(x, y)

def _unify_iterable(x, y):
    #print "unify sequences %s %s" % (x, y)
    idx, top = (-1, len(x)-1)
    while (idx < top):
        idx += 1
        xi, yi = x[idx], y[idx]
        if xi == yi: continue
        unify(xi, yi)

def _unify_mapping(x, y):
    #print "unify mappings %s %s" % (x, y)
    for xk in x.keys():
        xi, yi = x[xk], y[xk]
        if xi == yi: continue
        unify(xi, yi)

#-- memoizer for unify -----------------

_unification_memo = set()

def reset_memo():
    global _unification_memo
    _unification_memo.clear()

def check_and_memoize_pair(x, y):
    global _unification_memo
    elt = (id(x), id(y))
    if elt in _unification_memo:
        raise UnificationFailure(x, y)
    _unification_memo.add(elt)


def _both_are_bound(v1, v2):
    return v1.is_bound() and v2.is_bound()


#-- stream utility ---------

def stream_repr(*args):
    """represent streams of variables whose
       last element might be unbound"""
    repr_ = []
    for S in args:
        while S.is_bound():
            v = S.val
            if isinstance(v, tuple):
                v0 = v[0]
                if v0.is_bound():
                    repr_ += [str(v0.val), '|']
                else: repr_ += [str(v0), '|']
                S = v[1]
            else:
                repr_.append(str(v))
                break
        else:
            repr_.append(str(S))
        repr_.append(' ')
    repr_.pop()
    return ''.join(repr_)
