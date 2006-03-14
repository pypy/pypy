import threading
import time

#----------- Exceptions ---------------------------------
class VariableException(Exception):
    def __init__(self, name):
        self.name = name

class AlreadyBound(Exception):
    def __init__(self, var, val):
        print "can't bind %s to %s" % (var, val)
        self.var = var
        self.val = val
    
    def __str__(self):
        var, val = self.var, self.val
        return "can't bind %s to %s" % (var, val)

class NotAVariable(VariableException):
    def __str__(self):
        return "%s is not a variable" % self.name

#----------- Variables ----------------------------------
class EqSet(set): pass

class NoValue: pass

class NoDom: pass

class Var(object):
    """Spaceless dataflow variable"""
    _count_lock = threading.Lock()
    _vcount = 0
    
    def __init__(self, value=NoValue):
        try:
            Var._count_lock.acquire()
            self.name = str(Var._vcount)
        finally:
            Var._count_lock.release()
        Var._vcount += 1
        self._val = value
        # a condition variable for Wait
        self._value_condition = threading.Condition()
        # for WaitNeeded
        self._need_condition = threading.Condition()

    # value accessors
    def _set_val(self, val):
        if self._val != NoValue:
            if val != self._val:
                raise AlreadyBound(self, val)
        self._val = val
        
    def _get_val(self):
        return self._val
    val = property(_get_val, _set_val)

    def __str__(self):
        if self.is_bound():
            return "<%s>" % str(self._val)
        return "<?%s>" % self.name

    def __repr__(self):
        return self.__str__()

    # public interface

    def is_bound(self):
        return self.val != NoValue

    def is_free(self):
        return not self.isbound()
        
    def bind(self, val):
        self._value_condition.acquire()
        try:
            self.val = val
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
                    raise RuntimeError("possible deadlock??")
            return self.val
        finally:
            self._value_condition.release()

    def wait_needed(self):
        try:
            self._need_condition.acquire()
            self._need_condition.wait()
        finally:
            self._need_condition.release()

var = Var

#-- utility ---------

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

#-- to be killed soon ----

class CsVar(Var):
    """Dataflow variable linked to a space"""

    def __init__(self, name, cs):
        Var.__init__(self)
        if name in cs.names:
            raise AlreadyInStore(name)
        self.name = name
        # the creation-time (top-level) space
        self._cs = cs
        # top-level 'commited' binding
        self._val = NoValue
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
        try:
            if self._cs.in_transaction:
                if not self._changed:
                    self._previous = self._val
                    self._changed = True
            self._val = val
            self._value_condition.notifyAll()
        finally:
            self._value_condition.release()
        
    def _get_val(self):
        return self._val
    val = property(_get_val, _set_val)

    def bind(self, val):
        """home space bind"""
        self._cs.bind(self, val)

    is_bound = _is_bound

