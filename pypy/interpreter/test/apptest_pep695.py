"""
Application-level tests for PEP 695 (Type Parameter Syntax).
"""

# === Basic type alias tests ===

def test_simple_type_alias():
    type Point = tuple[float, float]
    assert Point.__name__ == 'Point'
    assert Point.__value__ == tuple[float, float]
    assert Point.__type_params__ == ()


def test_type_alias_repr():
    type MyAlias = int
    assert repr(MyAlias) == 'MyAlias'


# === Generic type alias tests ===

def test_generic_type_alias():
    type Stack[T] = list[T]
    assert Stack.__name__ == 'Stack'
    assert len(Stack.__type_params__) == 1
    assert Stack.__type_params__[0].__name__ == 'T'


def test_multiple_type_params():
    type Pair[T, U] = tuple[T, U]
    assert len(Pair.__type_params__) == 2
    T, U = Pair.__type_params__
    assert T.__name__ == 'T'
    assert U.__name__ == 'U'


def test_typevar_with_bound():
    type Bounded[T: int] = T
    T = Bounded.__type_params__[0]
    assert T.__name__ == 'T'
    assert T.__bound__ is int
    assert T.__constraints__ == ()


def test_typevar_with_constraints():
    type IntOrStr[T: (int, str)] = T
    T = IntOrStr.__type_params__[0]
    assert T.__name__ == 'T'
    assert T.__bound__ is None
    assert T.__constraints__ == (int, str)


# === ParamSpec tests ===

def test_paramspec_basic():
    from typing import Callable
    type CallableT[**P] = Callable[P, int]
    P = CallableT.__type_params__[0]
    assert P.__name__ == 'P'
    assert hasattr(P, 'args')
    assert hasattr(P, 'kwargs')


# === TypeVarTuple tests ===

def test_typevartuple_basic():
    type TupleT[*Ts] = tuple[*Ts]
    Ts = TupleT.__type_params__[0]
    assert Ts.__name__ == 'Ts'


# === Generic function tests ===

def test_generic_function():
    def identity[T](x: T) -> T:
        return x

    assert hasattr(identity, '__type_params__')
    assert len(identity.__type_params__) == 1
    assert identity.__type_params__[0].__name__ == 'T'


def test_generic_function_multiple_params():
    def pair[T, U](x: T, y: U) -> tuple[T, U]:
        return (x, y)

    assert len(pair.__type_params__) == 2
    T, U = pair.__type_params__
    assert T.__name__ == 'T'
    assert U.__name__ == 'U'


def test_generic_function_with_bound():
    def to_int[T: (int, float)](x: T) -> int:
        return int(x)

    T = to_int.__type_params__[0]
    assert T.__constraints__ == (int, float)


# === Generic class tests ===

def test_generic_class():
    class Stack[T]:
        def __init__(self):
            self.items: list[T] = []

        def push(self, item: T) -> None:
            self.items.append(item)

        def pop(self) -> T:
            return self.items.pop()

    assert hasattr(Stack, '__type_params__')
    assert len(Stack.__type_params__) == 1
    assert Stack.__type_params__[0].__name__ == 'T'


def test_generic_class_multiple_params():
    class Pair[T, U]:
        def __init__(self, first: T, second: U):
            self.first = first
            self.second = second

    assert len(Pair.__type_params__) == 2
    T, U = Pair.__type_params__
    assert T.__name__ == 'T'
    assert U.__name__ == 'U'


# === Lazy evaluation tests ===

def test_lazy_bound_evaluation():
    type LazyT[T: 1/0] = T
    # Definition should not raise - bound is lazy
    T = LazyT.__type_params__[0]
    # Accessing __bound__ triggers evaluation
    raises(ZeroDivisionError, getattr, T, '__bound__')


def test_lazy_value_evaluation():
    type LazyAlias = 1/0
    # Definition should not raise - value is lazy
    # Accessing __value__ triggers evaluation
    raises(ZeroDivisionError, getattr, LazyAlias, '__value__')


def test_lazy_constraints_evaluation():
    type LazyT[T: (int, 1/0)] = T
    T = LazyT.__type_params__[0]
    raises(ZeroDivisionError, getattr, T, '__constraints__')


# === Error cases ===

def test_invalid_expressions_in_annotation_scope():
    # Walrus operator not allowed
    with raises(SyntaxError):
        exec("type X = (y := int)")
    # yield not allowed
    with raises(SyntaxError):
        exec("type X = (yield 1)")
    # await not allowed
    with raises(SyntaxError):
        exec("type X = (await something)")


# === TypeAliasType class tests ===

def test_type_alias_type_creation():
    from _pypy_typing import TypeAliasType
    alias = TypeAliasType('MyType', lambda: int)
    assert alias.__name__ == 'MyType'
    assert alias.__value__ == int
    assert alias.__type_params__ == ()


def test_type_alias_type_subscript():
    type Stack[T] = list[T]
    result = Stack[int]
    assert result.__origin__ is Stack
    assert result.__args__ == (int,)


def test_type_alias_union():
    type IntAlias = int
    type StrAlias = str
    from typing import Union
    combined = IntAlias | StrAlias
    assert combined == Union[IntAlias, StrAlias]


# === __type_params__ attribute tests ===

def test_function_type_params_default():
    def regular_function():
        pass
    assert regular_function.__type_params__ == ()


def test_class_type_params_default():
    class RegularClass:
        pass
    assert RegularClass.__type_params__ == ()


def test_type_params_settable():
    def f():
        pass
    f.__type_params__ = (int, str)
    assert f.__type_params__ == (int, str)


def test_type_params_type_error():
    def f():
        pass
    raises(TypeError, setattr, f, '__type_params__', [1, 2, 3])


# === Known limitations and edge cases ===

def test_class_namespace_access_from_annotation_scope():
    """CPython 3.12+ supports class namespace access via __classdict__ cell,
    but PyPy doesn't yet. This test documents the current behavior."""
    class Outer:
        BaseType = int
        type Alias[T: BaseType] = list[T]

    # Accessing the bound triggers NameError because annotation scope
    # cannot access the class namespace
    T = Outer.Alias.__type_params__[0]
    raises(NameError, getattr, T, '__bound__')


def test_stacked_decorators_on_generic_function():
    call_order = []

    def d1(func):
        call_order.append('d1')
        return func

    def d2(func):
        call_order.append('d2')
        return func

    @d1
    @d2
    def generic_func[T](x: T) -> T:
        return x

    assert call_order == ['d2', 'd1']
    assert generic_func.__type_params__[0].__name__ == 'T'
    assert generic_func(42) == 42


def test_generic_method_inside_generic_class():
    class Container[T]:
        def __init__(self, value: T):
            self.value = value

        def transform[U](self, func) -> 'Container[U]':
            return Container(func(self.value))

    assert Container.__type_params__[0].__name__ == 'T'
    assert Container.transform.__type_params__[0].__name__ == 'U'

    c = Container(10)
    c2 = c.transform(str)
    assert c2.value == '10'


def test_forward_reference_in_type_alias():
    type NodeList = list[Node]

    class Node:
        pass

    assert NodeList.__value__ == list[Node]


def test_nested_generic_classes():
    class Outer[T]:
        class Inner[U]:
            def method(self, t: T, u: U):
                pass

    assert Outer.__type_params__[0].__name__ == 'T'
    assert Outer.Inner.__type_params__[0].__name__ == 'U'
