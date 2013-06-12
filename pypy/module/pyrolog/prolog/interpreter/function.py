from prolog.interpreter.term import Callable, Atom, Var
from prolog.interpreter.memo import EnumerationMemo
from prolog.interpreter.signature import Signature
from rpython.rlib import jit, objectmodel, unroll
from prolog.interpreter.helper import is_callable
# XXX needs tests

cutsig = Signature.getsignature("!", 0)
prefixsig = Signature.getsignature(":", 2)

class Rule(object):
    _immutable_ = True
    _immutable_fields_ = ["headargs[*]"]
    _attrs_ = ['next', 'head', 'headargs', 'contains_cut', 'body', 'size_env', 'signature', 'module']
    unrolling_attrs = unroll.unrolling_iterable(_attrs_)
    
    def __init__(self, head, body, module, next = None):
        from prolog.interpreter import helper
        head = head.dereference(None)
        assert isinstance(head, Callable)
        memo = EnumerationMemo()
        self.head = h = head.enumerate_vars(memo)
        if h.argument_count() > 0:
            self.headargs = h.arguments()
        else:
            self.headargs = None
        if body is not None:
            body = body.dereference(None)
            body = helper.ensure_callable(body)
            self.body = body.enumerate_vars(memo)
        else:
            self.body = None
        self.size_env = memo.size()
        self.signature = head.signature()        
        self._does_contain_cut()
        self.module = module
        self.next = next

    def _does_contain_cut(self):
        if self.body is None:
            self.contains_cut = False
            return
        stack = [self.body]
        while stack:
            current = stack.pop()
            if isinstance(current, Callable):
                if current.signature().eq(cutsig):
                    self.contains_cut = True
                    return
                else:
                    stack.extend(current.arguments())
        self.contains_cut = False

    @jit.unroll_safe
    def clone_and_unify_head(self, heap, head):
        env = [None] * self.size_env
        if self.headargs is not None:
            assert isinstance(head, Callable)
            for i in range(len(self.headargs)):
                arg2 = self.headargs[i]
                arg1 = head.argument_at(i)
                arg2.unify_and_standardize_apart(arg1, heap, env)
        body = self.body
        if body is None:
            return None
        return body.copy_standardize_apart(heap, env)

    def __repr__(self):
        if self.body is None:
            return "%s." % (self.head, )
        return "%s :- %s." % (self.head, self.body)

    def instance_copy(self):
        other = objectmodel.instantiate(Rule)
        for f in Rule.unrolling_attrs:
            setattr(other, f, getattr(self, f))
        return other
        
    def copy(self, stopat=None):
        first = self.instance_copy()
        curr = self.next
        copy = first
        while curr is not stopat:
            # if this is None, the stopat arg was invalid
            assert curr is not None
            new = curr.instance_copy()
            copy.next = new
            copy = new
            curr = curr.next
        return first, copy

    @jit.unroll_safe
    def find_applicable_rule(self, query):
        # This method should do some quick filtering on the rules to filter out
        # those that cannot match query. Here is where e.g. indexing should
        # occur.
        while self is not None:
            if self.headargs is not None:
                assert isinstance(query, Callable)
                for i in range(len(self.headargs)):
                    arg2 = self.headargs[i]
                    arg1 = query.argument_at(i)
                    if not arg2.quick_unify_check(arg1):
                        break
                else:
                    return self
            else:
                return self
            self = self.next
        return None

    def find_next_applicable_rule(self, query):
        if self.next is None:
            return None
        return self.next.find_applicable_rule(query)
    
    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__
    def __ne__(self, other):
        return not self == other


class Function(object):
    _immutable_fields_ = ["rulechain?", "meta_args?"]
    def __init__(self):
        self.meta_args = None
        self.rulechain = self.last = None

    @jit.unroll_safe
    def add_meta_prefixes(self, query, current_module):
        if not self.meta_args:
            return query
        numargs = query.argument_count()
        args = [None] * numargs
        for i in range(numargs):
            args[i] = self._prefix_argument(query.argument_at(i),
                    self.meta_args[i], current_module)
        return Callable.build(query.name(), args)

    def _prefix_argument(self, arg, meta_arg, module):
        if meta_arg in "0123456789:":
            if not (isinstance(arg, Callable) and arg.signature().eq(prefixsig)):
                return Callable.build(":", [module, arg])
        return arg

    def add_rule(self, rule, atend):
        if self.rulechain is None:
            self.rulechain = self.last = rule
        elif atend:
            self.rulechain, last = self.rulechain.copy()
            self.last = rule
            last.next = self.last
        else:
            rule.next = self.rulechain
            self.rulechain = rule

    def remove(self, rulechain):
        self.rulechain, last = self.rulechain.copy(rulechain)
        last.next = rulechain.next

