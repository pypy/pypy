import math
from pypy.rlib.objectmodel import we_are_translated, UnboxedValue
from pypy.rlib.rarithmetic import intmask
from pypy.lang.prolog.interpreter.error import UnificationFailed, UncatchableError

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
    def getvalue(self, frame):
        return self

    def dereference(self, frame):
        return self

    def get_max_var(self):
        return -1

    def clone(self, offset):
        return self

    def clone_compress_vars(self, vars_new_indexes, offset):
        return self

    def make_template(self, vars_new_indexes):
        return self

    def instantiate_template(self, template_frame):
        return self

    def get_unify_hash(self, frame=None):
        # if two non-var objects return two different numbers
        # they must not be unifiable
        raise NotImplementedError("abstract base class")

    def get_deeper_unify_hash(self, frame=None):
        return [self.get_unify_hash(frame)]

    def basic_unify(self, other, frame):
        pass

    def unify(self, other, frame, occurs_check=False):
        pass
    unify._annspecialcase_ = "specialize:arg(3)"

    def unify_with_template(self, other, frame, template_frame, to_instantiate):
        raise NotImplementedError("abstract base class")

    def contains_var(self, var, frame):
        return False

    def __eq__(self, other):
        # for testing
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class Var(PrologObject):#, UnboxedValue):
    TAG = 0
    STANDARD_ORDER = 0

    __slots__ = ('index', )

    def __init__(self, index):
        self.index = index

    def unify(self, other, frame, occurs_check=False):
        #debug_print("unify", self, other, frame.vars)
        self, val = self.get_last_var_in_chain_and_val(frame)
        if val is not None:
            other.unify(val, frame, occurs_check)
        elif isinstance(other, Var):
            other, val = other.get_last_var_in_chain_and_val(frame)
            if val is None:
                if other.index != self.index:
                    frame.setvar(self.index, other)
            else:
                self.unify(val, frame, occurs_check)
        else:
            if occurs_check and other.contains_var(self, frame):
                raise UnificationFailed()
            frame.setvar(self.index, other)
    unify._annspecialcase_ = "specialize:arg(3)"

    def unify_with_template(self, other, frame, template_frame, to_instantiate):
        self, val = self.get_last_var_in_chain_and_val(frame)
        if val is not None:
            return val.unify_with_template(other, frame, template_frame,
                                           to_instantiate)
        if isinstance(other, Var):
            other, otherval = other.get_last_var_in_chain_and_val(frame)
            if otherval is None:
                if other.index != self.index:
                    return frame.setvar(self.index, other)
            else:
                return self.unify_with_template(otherval, frame,
                                                template_frame, to_instantiate)
        else:
            if isinstance(other, TemplateVar):
                return other.unify_with_template(self, frame, template_frame,
                                                 to_instantiate)
            if isinstance(other, Term):
                to_instantiate.append((self.index, other))
            frame.setvar(self.index, other)

    def getvalue(self, frame):
        var, res = self.get_last_var_in_chain_and_val(frame)
        if res is not None:
            return res.getvalue(frame)
        return var

    def dereference(self, frame):
        var, res = self.get_last_var_in_chain_and_val(frame)
        if res is not None:
            return res
        return var

    def get_last_var_in_chain_and_val(self, frame):
        next = frame.getvar(self.index)
        if next is None or not isinstance(next, Var):
            return self, next
        # do path compression
        last, val = next.get_last_var_in_chain_and_val(frame)
        if val is None:
            frame.setvar(self.index, last)
        else:
            frame.setvar(self.index, val)
        return last, val

    def get_max_var(self):
        return self.index

    def clone(self, offset):
        return Var(self.index + offset)

    def clone_compress_vars(self, vars_new_indexes, offset):
        if self.index in vars_new_indexes:
            return Var(vars_new_indexes[self.index])
        index = len(vars_new_indexes) + offset
        vars_new_indexes[self.index] = index
        return Var(index)
    
    def make_template(self, vars_new_indexes):
        if self.index in vars_new_indexes:
            return TemplateVar.make_templatevar(vars_new_indexes[self.index])
        index = len(vars_new_indexes)
        vars_new_indexes[self.index] = index
        return TemplateVar.make_templatevar(index)

    def get_unify_hash(self, frame=None):
        if frame is None:
            return 0
        self = self.dereference(frame)
        if isinstance(self, Var):
            return 0
        return self.get_unify_hash(frame)

    def contains_var(self, var, frame):
        self = self.dereference(frame)
        if self is var:
            return True
        if not isinstance(self, Var):
            return self.contains_var(var, frame)
        return False

    def __repr__(self):
        return "Var(%s)" % (self.index, )


class TemplateVar(PrologObject):
    TAG = 0
    STANDARD_ORDER = 0
    __slots__ = 'index'
    cache = []

    def __init__(self, index):
        self.index = index

    def unify(self, other, frame, occurs_check=False):
        raise UncatchableError("TemplateVar in wrong place")

    def unify_with_template(self, other, frame, template_frame, to_instantiate):
        val = template_frame[self.index]
        if val is None:
            template_frame[self.index] = other
        else:
            val.unify_with_template(other, frame, template_frame, to_instantiate)

    def getvalue(self, frame):
        raise UncatchableError("TemplateVar in wrong place")

    def dereference(self, frame):
        raise UncatchableError("TemplateVar in wrong place")

    def get_max_var(self):
        return self.index

    def clone(self, offset):
        return TemplateVar.make_template(self.index + offset)

    def clone_compress_vars(self, vars_new_indexes, offset):
        raise UncatchableError("TemplateVar in wrong place")

    def make_template(self, vars_new_indexes):
        raise UncatchableError("TemplateVar in wrong place")

    def instantiate_template(self, template_frame):
        return template_frame[self.index]

    def get_unify_hash(self, frame=None):
        return 0

    def contains_var(self, var, frame):
        raise UncatchableError("TemplateVar in wrong place")

    def __repr__(self):
        return "TemplateVar(%s)" % (self.index, )

    def make_templatevar(index):
        l = len(TemplateVar.cache)
        if index >= l:
            TemplateVar.cache.extend(
                [TemplateVar(i) for i in range(l, l + index + 1)])
        return TemplateVar.cache[index]
    make_templatevar = staticmethod(make_templatevar)


class Callable(PrologObject):
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

    def basic_unify(self, other, frame):
        if isinstance(other, Atom):
            if self is other or other.name == self.name:
                return
        raise UnificationFailed

    def unify(self, other, frame, occurs_check=False):
        #debug_print("unify", self, other, type(other))
        if isinstance(other, Var):
            return other.unify(self, frame, occurs_check)
        return self.basic_unify(other, frame)
    unify._annspecialcase_ = "specialize:arg(3)"

    def unify_with_template(self, other, frame, template_frame, to_instantiate):
        if isinstance(other, Var):
            return other.unify_with_template(self, frame, template_frame, to_instantiate)
        elif isinstance(other, TemplateVar):
            return other.unify_with_template(self, frame, template_frame, to_instantiate)
        return self.basic_unify(other, frame)

    def get_unify_hash(self, frame=None):
        return intmask(hash(self.name) << TAGBITS | self.TAG)

    def get_prolog_signature(self):
        return Term("/", [self, Number(0)])

    def make_atom(name):
        result = Atom.cache.get(name, None)
        if result is not None:
            return result
        Atom.cache[name] = result = Atom(name)
        return result
    make_atom = staticmethod(make_atom)

class Number(PrologObject):
    TAG = tag()
    STANDARD_ORDER = 2
    def __init__(self, num):
        self.num = num

    def basic_unify(self, other, frame):
        if isinstance(other, Number):
            if other.num != self.num:
                raise UnificationFailed
            return
        raise UnificationFailed

    def unify(self, other, frame, occurs_check=False):
        #debug_print("unify", self, other, type(other))
        if isinstance(other, Var):
            return other.unify(self, frame, occurs_check)
        return self.basic_unify(other, frame)
    unify._annspecialcase_ = "specialize:arg(3)"

    def unify_with_template(self, other, frame, template_frame, to_instantiate):
        if isinstance(other, Var):
            return other.unify_with_template(self, frame, template_frame, to_instantiate)
        elif isinstance(other, TemplateVar):
            return other.unify_with_template(self, frame, template_frame, to_instantiate)
        return self.basic_unify(other, frame)

    def __str__(self):
        return repr(self.num)

    def __repr__(self):
        return "Number(%r)" % (self.num, )

    def get_unify_hash(self, frame=None):
        return intmask(self.num << TAGBITS | self.TAG)


class Float(PrologObject):
    TAG = tag()
    STANDARD_ORDER = 2
    def __init__(self, num):
        self.num = num

    def basic_unify(self, other, frame):
        if isinstance(other, Float):
            if other.num != self.num:
                raise UnificationFailed
            return
        raise UnificationFailed

    def basic_unify(self, other, frame):
        if isinstance(other, Float):
            if other.num != self.num:
                raise UnificationFailed
            return
        raise UnificationFailed

    def unify(self, other, frame, occurs_check=False):
        if isinstance(other, Var):
            return other.unify(self, frame, occurs_check)
        return self.basic_unify(other, frame)
    unify._annspecialcase_ = "specialize:arg(3)"

    def unify_with_template(self, other, frame, template_frame, to_instantiate):
        if isinstance(other, Var):
            return other.unify_with_template(self, frame, template_frame, to_instantiate)
        elif isinstance(other, TemplateVar):
            return other.unify_with_template(self, frame, template_frame, to_instantiate)
        return self.basic_unify(other, frame)

    def get_unify_hash(self, frame=None):
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

def _make_template(obj, vars_new_indexes):
    return obj.make_template(vars_new_indexes)

def _instantiate_template(obj, template_frame):
    return obj.instantiate_template(template_frame)

def _getvalue(obj, frame):
    return obj.getvalue(frame)

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

    def unify(self, other, frame, occurs_check=False):
        if not isinstance(other, Term):
            if isinstance(other, Var):
                return other.unify(self, frame, occurs_check)
            raise UnificationFailed
        if (hash(self.name) != hash(other.name) or 
            self.name != other.name or len(self.args) != len(other.args)):
            raise UnificationFailed
        for i in range(len(self.args)):
            self.args[i].unify(other.args[i], frame, occurs_check)
    unify._annspecialcase_ = "specialize:arg(3)"

    def unify_with_template(self, other, frame, template_frame, to_instantiate):
        if not isinstance(other, Term):
            if isinstance(other, Var):
                return other.unify_with_template(self, frame, template_frame, to_instantiate)
            if isinstance(other, TemplateVar):
                return other.unify_with_template(self, frame, template_frame, to_instantiate)
            raise UnificationFailed
        if (hash(self.name) != hash(other.name) or 
            self.name != other.name or len(self.args) != len(other.args)):
            raise UnificationFailed
        for i in range(len(self.args)):
            self.args[i].unify_with_template(other.args[i], frame,
                                             template_frame, to_instantiate)

    def get_max_var(self):
        result = -1
        for subterm in self.args:
            result = max(result, subterm.get_max_var())
        return result
    
    def clone(self, offset):
        return self._copy_term(_clone, offset)

    def clone_compress_vars(self, vars_new_indexes, offset):
        return self._copy_term(_clone_compress_vars, vars_new_indexes, offset)

    def make_template(self, vars_new_indexes):
        return self._copy_term(_make_template, vars_new_indexes)

    def instantiate_template(self, template_frame):
        return self._copy_term(_instantiate_template, template_frame)

    def getvalue(self, frame):
        return self._copy_term(_getvalue, frame)

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
    _copy_term._annspecialcase_ = "specialize:arg(1)"

    def get_unify_hash(self, frame=None):
        return intmask(hash(self.signature) << TAGBITS | self.TAG)

    def get_deeper_unify_hash(self, frame=None):
        result = [0] * len(self.args)
        for i in range(len(self.args)):
            result[i] = self.args[i].get_unify_hash(frame)
        return result

    def get_prolog_signature(self):
        return Term("/", [Atom.make_atom(self.name), Number(len(self.args))])
    
    def contains_var(self, var, frame):
        for arg in self.args:
            if arg.contains_var(var, frame):
                return True
        return False
        

class Rule(object):
    def __init__(self, head, body):
        from pypy.lang.prolog.interpreter import helper
        d = {}
        head = head.make_template(d)
        assert isinstance(head, Callable)
        self.head = head
        if body is not None:
            body = helper.ensure_callable(body)
            self.body = body.make_template(d)
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

    def clone(self, offset):
        if self.body is None:
            body = None
        else:
            body = self.body.clone(offset)
        return Rule(self.head.clone(offset), body)

    def clone_and_unify_head(self, frame, head):
        template_frame = [None] * self.numvars
        if isinstance(head, Term):
            to_instantiate = []
            h2 = self.head
            assert isinstance(h2, Term)
            for i in range(len(h2.args)):
                arg1 = h2.args[i]
                arg2 = head.args[i]
                if (isinstance(arg1, Term) or
                    isinstance(arg1, TemplateVar)):
                    h2.args[i].unify_with_template(
                        head.args[i], frame, template_frame, to_instantiate)
                else:
                    h2.args[i].unify(head.args[i], frame)
            extend_and_normalize_template_frame(template_frame, frame)
            for index, obj in to_instantiate:
                frame.vars[index] = obj.instantiate_template(template_frame)
        else:
            next_free = frame.maxvar()
            for i in range(self.numvars):
                template_frame[i] = Var(next_free)
                next_free += 1
            frame.extend(next_free - frame.maxvar())
        body = self.body
        if body is None:
            return None
        return body.instantiate_template(template_frame)

    def __repr__(self):
        if self.body is None:
            return "%s." % (self.head, )
        return "%s :- %s." % (self.head, self.body)


def extend_and_normalize_template_frame(template_frame, frame):
    next_free = frame.maxvar()
    for i in range(len(template_frame)):
        val = template_frame[i]
        if val is None:
            template_frame[i] = Var(next_free)
            next_free += 1
        elif isinstance(val, TemplateVar):
            template_frame[i] = template_frame[val.index]
    frame.extend(next_free - frame.maxvar())

def rcmp(a, b): # RPython does not support cmp...
    if a == b:
        return 0
    if a < b:
        return -1
    return 1
rcmp._annspecialcase_ = "specialize:argtype(0)"

def cmp_standard_order(obj1, obj2, frame):
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
            a1 = obj1.args[i].dereference(frame)
            a2 = obj2.args[i].dereference(frame)
            c = cmp_standard_order(a1, a2, frame)
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
