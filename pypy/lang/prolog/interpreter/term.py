import math
from pypy.rlib.objectmodel import we_are_translated, UnboxedValue
from pypy.rlib.rarithmetic import intmask
from pypy.lang.prolog.interpreter.error import UnificationFailed, UncatchableError
from pypy.rlib.objectmodel import hint, specialize

DEBUG = True

TAGBITS = 3
CURR_TAG = 1
def tag():
    global CURR_TAG
    CURR_TAG += 1
    assert CURR_TAG <= 2 ** TAGBITS
    return CURR_TAG

def debug_print(*args):
    if DEBUG and not we_are_translated():
        print " ".join([str(a) for a in args])

class PrologObject(object):
    __slots__ = ()
    def getvalue(self, heap):
        return self

    def dereference(self, heap):
        raise NotImplementedError("abstract base class")

    def get_max_var(self):
        return -1

    def copy(self, heap, memo):
        raise NotImplementedError("abstract base class")

    def copy_and_unify(self, other, heap, memo):
        raise NotImplementedError("abstract base class")

    def clone_compress_vars(self, vars_new_indexes, offset):
        return self

    def get_unify_hash(self, heap=None):
        # if two non-var objects return two different numbers
        # they must not be unifiable
        raise NotImplementedError("abstract base class")

    def get_deeper_unify_hash(self, heap=None):
        return [self.get_unify_hash(heap)]

    @specialize.arg(3)
    def unify(self, other, heap, occurs_check=False):
        raise NotImplementedError("abstract base class")

    @specialize.arg(3)
    def _unify(self, other, heap, occurs_check=False):
        raise NotImplementedError("abstract base class")

    def contains_var(self, var, heap):
        return False

    def __eq__(self, other):
        # for testing
        return (self.__class__ == other.__class__ and
                self.__dict__ == other.__dict__)

    def __ne__(self, other):
        # for testing
        return not (self == other)


class Var(PrologObject):
    TAG = 0
    STANDARD_ORDER = 0

    __slots__ = ('index', )

    def __init__(self, index):
        self.index = index

    @specialize.arg(3)
    def unify(self, other, heap, occurs_check=False):
        return self.dereference(heap)._unify(other, heap, occurs_check)

    @specialize.arg(3)
    def _unify(self, other, heap, occurs_check=False):
        other = other.dereference(heap)
        if isinstance(other, Var) and other is self:
            pass
        elif occurs_check and other.contains_var(self, heap):
            raise UnificationFailed()
        else:
            heap.setvar(self.index, other)

    def dereference(self, heap):
        next = heap.getvar(self.index)
        if next is None:
            return self
        else:
            result = next.dereference(heap)
            # do path compression
            heap.setvar(self.index, result)
            return result

    def getvalue(self, heap):
        res = self.dereference(heap)
        if not isinstance(res, Var):
            return res.getvalue(heap)
        return res

    def copy(self, heap, memo):
        hint(self, concrete=True)
        try:
            return memo[self.index]
        except KeyError:
            newvar = memo[self.index] = heap.newvar()
            return newvar

    def copy_and_unify(self, other, heap, memo):
        hint(self, concrete=True)
        try:
            seen_value = memo[self.index]
        except KeyError:
            memo[self.index] = other
            return other
        else:
            seen_value.unify(other, heap)
            return seen_value


    def get_max_var(self):
        return self.index

    def clone_compress_vars(self, vars_new_indexes, offset):
        if self.index in vars_new_indexes:
            return Var(vars_new_indexes[self.index])
        index = len(vars_new_indexes) + offset
        vars_new_indexes[self.index] = index
        return Var(index)
    
    def get_unify_hash(self, heap=None):
        if heap is None:
            return 0
        self = self.dereference(heap)
        if isinstance(self, Var):
            return 0
        return self.get_unify_hash(heap)

    def contains_var(self, var, heap):
        self = self.dereference(heap)
        if self is var:
            return True
        if not isinstance(self, Var):
            return self.contains_var(var, heap)
        return False

    def __repr__(self):
        return "Var(%s)" % (self.index, )


    def __eq__(self, other):
        # for testing
        return (self.__class__ == other.__class__ and
                self.index == other.index)

class NonVar(PrologObject):

    def dereference(self, heap):
        return self

    @specialize.arg(3)
    def unify(self, other, heap, occurs_check=False):
        return self._unify(other, heap, occurs_check)


    @specialize.arg(3)
    def basic_unify(self, other, heap, occurs_check=False):
        raise NotImplementedError("abstract base class")

    @specialize.arg(3)
    def _unify(self, other, heap, occurs_check=False):
        other = other.dereference(heap)
        if isinstance(other, Var):
            other._unify(self, heap, occurs_check)
        else:
            self.basic_unify(other, heap, occurs_check)

    def copy_and_unify(self, other, heap, memo):
        other = other.dereference(heap)
        if isinstance(other, Var):
            copy = self.copy(heap, memo)
            other._unify(copy, heap)
            return copy
        else:
            return self.copy_and_basic_unify(other, heap, memo)

    def copy_and_basic_unify(self, other, heap, memo):
        raise NotImplementedError("abstract base class")


class Callable(NonVar):
    name = ""
    signature = ""

    def get_prolog_signature(self):
        raise NotImplementedError("abstract base")


class Atom(Callable):
    TAG = tag()
    STANDARD_ORDER = 1

    cache = {}

    def __init__(self, name):
        self.name = name
        self.signature = self.name + "/0"

    def __str__(self):
        return self.name

    def __repr__(self):
        return "Atom(%r)" % (self.name,)

    @specialize.arg(3)
    def basic_unify(self, other, heap, occurs_check=False):
        if isinstance(other, Atom) and (self is other or
                                        other.name == self.name):
            return
        raise UnificationFailed

    def copy(self, heap, memo):
        return self

    def copy_and_basic_unify(self, other, heap, memo):
        hint(self, concrete=True)
        if isinstance(other, Atom) and (self is other or
                                        other.name == self.name):
            return self
        else:
            raise UnificationFailed

    def get_unify_hash(self, heap=None):
        return intmask(hash(self.name) << TAGBITS | self.TAG)

    def get_prolog_signature(self):
        return Term("/", [self, Number(0)])

    def newatom(name):
        result = Atom.cache.get(name, None)
        if result is not None:
            return result
        Atom.cache[name] = result = Atom(name)
        return result
    newatom = staticmethod(newatom)


class Number(NonVar):
    TAG = tag()
    STANDARD_ORDER = 2
    def __init__(self, num):
        self.num = num

    @specialize.arg(3)
    def basic_unify(self, other, heap, occurs_check=False):
        if isinstance(other, Number) and other.num == self.num:
            return
        raise UnificationFailed

    def copy(self, heap, memo):
        return self

    def copy_and_basic_unify(self, other, heap, memo):
        hint(self, concrete=True)
        if isinstance(other, Number) and other.num == self.num:
            return self
        else:
            raise UnificationFailed

    def __str__(self):
        return repr(self.num)

    def __repr__(self):
        return "Number(%r)" % (self.num, )

    def get_unify_hash(self, heap=None):
        return intmask(self.num << TAGBITS | self.TAG)


class Float(NonVar):
    TAG = tag()
    STANDARD_ORDER = 2
    def __init__(self, num):
        self.num = num

    @specialize.arg(3)
    def basic_unify(self, other, heap, occurs_check=False):
        if isinstance(other, Float) and other.num == self.num:
            return
        raise UnificationFailed

    def copy(self, heap, memo):
        return self

    def copy_and_basic_unify(self, other, heap, memo):
        hint(self, concrete=True)
        if isinstance(other, Float) and other.num == self.num:
            return self
        else:
            raise UnificationFailed

    def get_unify_hash(self, heap=None):
        #XXX no clue whether this is a good idea...
        m, e = math.frexp(self.num)
        m = intmask(int(m / 2 * 2 ** (32 - TAGBITS)))
        return intmask(m << TAGBITS | self.TAG)

    def __str__(self):
        return repr(self.num)

    def __repr__(self):
        return "Float(%r)" % (self.num, )


# helper functions for various Term methods

def _clone(obj, offset):
    return obj.clone(offset)

def _clone_compress_vars(obj, vars_new_indexes, offset):
    return obj.clone_compress_vars(vars_new_indexes, offset)

def _getvalue(obj, heap):
    return obj.getvalue(heap)

class Term(Callable):
    TAG = tag()
    STANDARD_ORDER = 3
    def __init__(self, name, args, signature=None):
        self.name = name
        self.args = args
        if signature is None:
            self.signature = name + "/" + str(len(args))
        else:
            self.signature = signature

    def __repr__(self):
        return "Term(%r, %r)" % (self.name, self.args)

    def __str__(self):
        return "%s(%s)" % (self.name, ", ".join([str(a) for a in self.args]))

    @specialize.arg(3)
    def basic_unify(self, other, heap, occurs_check=False):
        if (isinstance(other, Term) and
            self.name == other.name and
            len(self.args) == len(other.args)):
            for i in range(len(self.args)):
                self.args[i].unify(other.args[i], heap, occurs_check)
        else:
            raise UnificationFailed

    def copy(self, heap, memo):
        hint(self, concrete=True)
        self = hint(self, deepfreeze=True)
        newargs = []
        i = 0
        while i < len(self.args):
            hint(i, concrete=True)
            arg = self.args[i].copy(heap, memo)
            newargs.append(arg)
            i += 1
        return Term(self.name, newargs)

    def copy_and_basic_unify(self, other, heap, memo):
        hint(self, concrete=True)
        self = hint(self, deepfreeze=True)
        if (isinstance(other, Term) and
            self.name == other.name and
            len(self.args) == len(other.args)):
            newargs = [None] * len(self.args)
            i = 0
            while i < len(self.args):
                hint(i, concrete=True)
                arg = self.args[i].copy_and_unify(other.args[i], heap, memo)
                newargs[i] = arg
                i += 1
            return Term(self.name, newargs)
        else:
            raise UnificationFailed

    def get_max_var(self):
        result = -1
        for subterm in self.args:
            result = max(result, subterm.get_max_var())
        return result
    
    def clone_compress_vars(self, vars_new_indexes, offset):
        return self._copy_term(_clone_compress_vars, vars_new_indexes, offset)

    def getvalue(self, heap):
        return self._copy_term(_getvalue, heap)

    def _copy_term(self, copy_individual, *extraargs):
        args = [None] * len(self.args)
        newinstance = False
        for i in range(len(self.args)):
            arg = self.args[i]
            cloned = copy_individual(arg, *extraargs)
            if cloned is not arg:
                newinstance = True
            args[i] = cloned
        if newinstance:
            return Term(self.name, args, self.signature)
        else:
            return self

    def get_unify_hash(self, heap=None):
        return intmask(hash(self.signature) << TAGBITS | self.TAG)

    def get_deeper_unify_hash(self, heap=None):
        result = [0] * len(self.args)
        for i in range(len(self.args)):
            result[i] = self.args[i].get_unify_hash(heap)
        return result

    def get_prolog_signature(self):
        return Term("/", [Atom.newatom(self.name), Number(len(self.args))])
    
    def contains_var(self, var, heap):
        for arg in self.args:
            if arg.contains_var(var, heap):
                return True
        return False
        

class Rule(object):
    def __init__(self, head, body):
        from pypy.lang.prolog.interpreter import helper
        d = {}
        head = head.clone_compress_vars(d, 0)
        assert isinstance(head, Callable)
        self.head = head
        if body is not None:
            body = helper.ensure_callable(body)
            self.body = body.clone_compress_vars(d, 0)
        else:
            self.body = None
        self.numvars = len(d)
        self.signature = self.head.signature
        self.unify_hash = self.head.get_deeper_unify_hash()
        self._does_contain_cut()

    def _does_contain_cut(self):
        if self.body is None:
            self.contains_cut = False
            return
        stack = [self.body]
        while stack:
            current = stack.pop()
            if isinstance(current, Atom):
                if current.name == "!":
                    self.contains_cut = True
                    return
            elif isinstance(current, Term):
                stack.extend(current.args)
        self.contains_cut = False

    def clone_and_unify_head(self, heap, head):
        memo = {}
        if isinstance(head, Term):
            h2 = self.head
            assert isinstance(h2, Term)
            for i in range(len(h2.args)):
                arg1 = h2.args[i]
                arg2 = head.args[i]
                arg1.copy_and_unify(arg2, heap, memo)
        body = self.body
        if body is None:
            return None
        return body.copy(heap, memo)

    def __repr__(self):
        if self.body is None:
            return "%s." % (self.head, )
        return "%s :- %s." % (self.head, self.body)


@specialize.argtype(0)
def rcmp(a, b): # RPython does not support cmp...
    if a == b:
        return 0
    if a < b:
        return -1
    return 1

def cmp_standard_order(obj1, obj2, heap):
    c = rcmp(obj1.STANDARD_ORDER, obj2.STANDARD_ORDER)
    if c != 0:
        return c
    if isinstance(obj1, Var):
        assert isinstance(obj2, Var)
        return rcmp(obj1.index, obj2.index)
    if isinstance(obj1, Atom):
        assert isinstance(obj2, Atom)
        return rcmp(obj1.name, obj2.name)
    if isinstance(obj1, Term):
        assert isinstance(obj2, Term)
        c = rcmp(len(obj1.args), len(obj2.args))
        if c != 0:
            return c
        c = rcmp(obj1.name, obj2.name)
        if c != 0:
            return c
        for i in range(len(obj1.args)):
            a1 = obj1.args[i].dereference(heap)
            a2 = obj2.args[i].dereference(heap)
            c = cmp_standard_order(a1, a2, heap)
            if c != 0:
                return c
        return 0
    # XXX hum
    if isinstance(obj1, Number):
        if isinstance(obj2, Number):
            return rcmp(obj1.num, obj2.num)
        elif isinstance(obj2, Float):
            return rcmp(obj1.num, obj2.num)
    if isinstance(obj1, Float):
        if isinstance(obj2, Number):
            return rcmp(obj1.num, obj2.num)
        elif isinstance(obj2, Float):
            return rcmp(obj1.num, obj2.num)
    assert 0
