from prolog.interpreter.function import Rule, Function
from prolog.interpreter.term import Callable
from prolog.interpreter.signature import Signature
from prolog.interpreter.continuation import Engine

class C(Callable):
    def __init__(self, name):
        self._name = name
    def __eq__(self, other):
        return self.name()== other.name()    
    def __str__(self):
        return 'C(%s)' % self.name()    
    def signature(self):
        return Signature(self.name(), 123)
    def name(self):
        return 'C'
    def argument_count(self):
        return 0
    def arguments(self):
        return []
    __repr__ = __str__

def test_copy():
 
    e = Engine()
    m = e.modulewrapper
    l1 = Rule(C('a'), C('a1'), m.user_module, Rule(C('b'), C('b1'),
            m.user_module, Rule(C('c'), C('c1'), m.user_module)))
    l1c, _ = l1.copy()

    t1 = l1
    t2 = l1c
    while t1 is not None:
        assert t1 is not t2
        assert t1 == t2
        t1 = t1.next
        t2 = t2.next

    l0 = Rule(C(-1), C('a'), m.user_module, Rule(C(-2), C('b'),
            m.user_module, Rule(C(-3), C('c'), m.user_module, l1)))
    l0c, end = l0.copy(l1)
    t1 = l0
    t2 = l0c
    while t1 is not l1:
        assert t1 == t2
        assert t1 is not t2
        t1 = t1.next
        prev = t2
        t2 = t2.next
    assert t2 is l1
    assert prev is end
    
def test_function():
    e = Engine()
    m = e.modulewrapper
    def get_rules(chain):
        r = []
        while chain:
            r.append((chain.head, chain.body))
            chain = chain.next
        return r
    f = Function()
    r1 = Rule(C(1), C(2), m.user_module)
    r2 = Rule(C(2), C(3), m.user_module)
    r3 = Rule(C(0), C(0), m.user_module)
    r4 = Rule(C(15), C(-1), m.user_module)
    f.add_rule(r1, True)
    assert get_rules(f.rulechain) == [(C(1), C(2))]
    f.add_rule(r2, True)
    assert get_rules(f.rulechain) == [(C(1), C(2)), (C(2), C(3))]
    f.add_rule(r3, False)
    assert get_rules(f.rulechain) == [(C(0), C(0)), (C(1), C(2)), (C(2), C(3))]

    # test logical update view
    rulechain = f.rulechain
    f.add_rule(r4, True)
    assert get_rules(rulechain) == [(C(0), C(0)), (C(1), C(2)), (C(2), C(3))]
    assert get_rules(f.rulechain) == [(C(0), C(0)), (C(1), C(2)), (C(2), C(3)), (C(15), C(-1))]
