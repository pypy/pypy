import threading

#----------- Exceptions ---------------------------------
class VariableException(Exception):
    def __init__(self, name):
        self.name = name

class AlreadyInStore(VariableException):
    def __str__(self):
        return "%s already in store" % self.name

class AlreadyBound(Exception):
    def __init__(self, var, val):
        self.var = var
        self.val = val
    
    def __str__(self):
        return "%s:%s already bound to %s" % (self.var.name,
                                              self.var.val,
                                              self.val)

class NotAVariable(VariableException):
    def __str__(self):
        return "%s is not a variable" % self.name

#----------- Variables ----------------------------------
class EqSet(set): pass

class NoValue: pass

class NoDom: pass

class SimpleVar(object):
    """Spaceless dataflow variable"""
    
    def __init__(self):
        self.name = str(id(self))
        self._val = NoValue
        # a condition variable for concurrent access
        self._value_condition = threading.Condition()

    # value accessors
    def _set_val(self, val):
        self._value_condition.acquire()
        try:
            if self._val != NoValue:
                if val != self._val:
                    raise AlreadyBound(self, val)
            self._val = val
            self._value_condition.notifyAll()
        finally:
            self._value_condition.release()
        
    def _get_val(self):
        return self._val
    val = property(_get_val, _set_val)


    # public interface

    def is_bound(self):
        return self.val != NoValue

    def bind(self, val):
        self.val = val

    def get(self):
        """Make threads wait on the variable
           being bound in the top-level space
        """
        try:
            self._value_condition.acquire()
            while not self.is_bound():
                self._value_condition.wait()
            return self.val
        finally:
            self._value_condition.release()


class CsVar(SimpleVar):
    """Dataflow variable linked to a space"""

    def __init__(self, name, cs):
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

    def __str__(self):
        if self.is_bound():
            return "%s = %s" % (self.name, self.val)
        return "%s" % self.name

    def __repr__(self):
        return self.__str__()

    def bind(self, val):
        """home space bind"""
        self._cs.bind(self, val)

    is_bound = _is_bound
