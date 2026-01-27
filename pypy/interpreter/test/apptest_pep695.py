"""
Application-level tests for PEP 695 (Type Parameter Syntax).

These tests run on the interpreted PyPy.
"""

# === Basic type alias tests ===

def test_simple_type_alias():
    """Test: type Point = tuple[float, float]"""
    type Point = tuple[float, float]
    assert Point.__name__ == 'Point'
    assert Point.__value__ == tuple[float, float]
    assert Point.__type_params__ == ()


def test_type_alias_with_int():
    """Test: type IntList = list[int]"""
    type IntList = list[int]
    assert IntList.__name__ == 'IntList'
    assert IntList.__value__ == list[int]


def test_type_alias_repr():
    """Test that TypeAliasType has correct repr."""
    type MyAlias = int
    assert repr(MyAlias) == 'MyAlias'


# === Generic type alias tests ===

def test_generic_type_alias():
    """Test: type Stack[T] = list[T]"""
    type Stack[T] = list[T]
    assert Stack.__name__ == 'Stack'
    assert len(Stack.__type_params__) == 1
    T = Stack.__type_params__[0]
    assert T.__name__ == 'T'


def test_multiple_type_params():
    """Test: type Pair[T, U] = tuple[T, U]"""
    type Pair[T, U] = tuple[T, U]
    assert Pair.__name__ == 'Pair'
    assert len(Pair.__type_params__) == 2
    T, U = Pair.__type_params__
    assert T.__name__ == 'T'
    assert U.__name__ == 'U'


# === TypeVar with bound tests ===

def test_typevar_with_bound():
    """Test: type Bounded[T: int] = T"""
    type Bounded[T: int] = T
    T = Bounded.__type_params__[0]
    assert T.__name__ == 'T'
    assert T.__bound__ == int
    assert T.__constraints__ == ()


def test_typevar_with_complex_bound():
    """Test TypeVar with more complex bound expression."""
    from typing import Hashable
    type HashableT[T: Hashable] = list[T]
    T = HashableT.__type_params__[0]
    assert T.__bound__ == Hashable


# === TypeVar with constraints tests ===

def test_typevar_with_constraints():
    """Test: type IntOrStr[T: (int, str)] = T"""
    type IntOrStr[T: (int, str)] = T
    T = IntOrStr.__type_params__[0]
    assert T.__name__ == 'T'
    assert T.__bound__ is None
    assert T.__constraints__ == (int, str)


def test_typevar_three_constraints():
    """Test TypeVar with three constraints."""
    type NumericT[T: (int, float, complex)] = T
    T = NumericT.__type_params__[0]
    assert T.__constraints__ == (int, float, complex)


# === ParamSpec tests ===

def test_paramspec_basic():
    """Test: type Callable[**P] = ..."""
    from typing import Callable
    type CallableT[**P] = Callable[P, int]
    P = CallableT.__type_params__[0]
    assert P.__name__ == 'P'
    # ParamSpec has args and kwargs attributes
    assert hasattr(P, 'args')
    assert hasattr(P, 'kwargs')


# === TypeVarTuple tests ===

def test_typevartuple_basic():
    """Test: type Tuple[*Ts] = tuple[*Ts]"""
    type TupleT[*Ts] = tuple[*Ts]
    Ts = TupleT.__type_params__[0]
    assert Ts.__name__ == 'Ts'


# === Generic function tests ===

def test_generic_function():
    """Test: def identity[T](x: T) -> T: return x"""
    def identity[T](x: T) -> T:
        return x

    assert hasattr(identity, '__type_params__')
    assert len(identity.__type_params__) == 1
    T = identity.__type_params__[0]
    assert T.__name__ == 'T'


def test_generic_function_multiple_params():
    """Test function with multiple type parameters."""
    def pair[T, U](x: T, y: U) -> tuple[T, U]:
        return (x, y)

    assert len(pair.__type_params__) == 2
    T, U = pair.__type_params__
    assert T.__name__ == 'T'
    assert U.__name__ == 'U'


def test_generic_function_with_bound():
    """Test function with bounded type parameter."""
    def to_int[T: (int, float)](x: T) -> int:
        return int(x)

    T = to_int.__type_params__[0]
    assert T.__constraints__ == (int, float)


# === Generic class tests ===

def test_generic_class():
    """Test: class Stack[T]: ..."""
    class Stack[T]:
        def __init__(self):
            self.items: list[T] = []

        def push(self, item: T) -> None:
            self.items.append(item)

        def pop(self) -> T:
            return self.items.pop()

    assert hasattr(Stack, '__type_params__')
    assert len(Stack.__type_params__) == 1
    T = Stack.__type_params__[0]
    assert T.__name__ == 'T'


def test_generic_class_multiple_params():
    """Test class with multiple type parameters."""
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
    """Test that TypeVar bound is lazily evaluated."""
    # The bound expression should not be evaluated until __bound__ is accessed
    evaluated = []

    class BoundMarker:
        def __class_getitem__(cls, item):
            evaluated.append(item)
            return int

    type LazyT[T: BoundMarker['test']] = T

    # Should not have evaluated yet
    assert evaluated == []

    # Now access the bound - should trigger evaluation
    T = LazyT.__type_params__[0]
    _ = T.__bound__
    assert 'test' in evaluated


def test_lazy_value_evaluation():
    """Test that type alias value is lazily evaluated."""
    evaluated = []

    class ValueMarker:
        def __class_getitem__(cls, item):
            evaluated.append(item)
            return list[item]

    type LazyAlias = ValueMarker['test']

    # Should not have evaluated yet
    assert evaluated == []

    # Now access the value - should trigger evaluation
    _ = LazyAlias.__value__
    assert 'test' in evaluated


# === Error cases ===

def test_walrus_in_annotation_scope():
    """Test that walrus operator is not allowed in annotation scope."""
    import pytest
    with pytest.raises(SyntaxError):
        exec("type X = (y := int)")


def test_yield_in_annotation_scope():
    """Test that yield is not allowed in annotation scope."""
    import pytest
    with pytest.raises(SyntaxError):
        exec("type X = (yield 1)")


def test_await_in_annotation_scope():
    """Test that await is not allowed in annotation scope."""
    import pytest
    # Note: await outside async function is also an error
    with pytest.raises(SyntaxError):
        exec("type X = (await something)")


# === TypeAliasType class tests ===

def test_type_alias_type_creation():
    """Test creating TypeAliasType directly."""
    from _pypy_typing import TypeAliasType

    alias = TypeAliasType('MyType', lambda: int)
    assert alias.__name__ == 'MyType'
    assert alias.__value__ == int
    assert alias.__type_params__ == ()


def test_type_alias_type_subscript():
    """Test subscripting a TypeAliasType."""
    type Stack[T] = list[T]
    # Subscripting should return a generic alias
    result = Stack[int]
    # The result should be usable as a type hint


def test_type_alias_union():
    """Test using | with TypeAliasType."""
    type IntAlias = int
    type StrAlias = str

    # Union should work
    from typing import Union
    combined = IntAlias | StrAlias
    assert combined == Union[IntAlias, StrAlias]


# === __type_params__ attribute tests ===

def test_function_type_params_default():
    """Test that regular functions have empty __type_params__."""
    def regular_function():
        pass

    assert regular_function.__type_params__ == ()


def test_class_type_params_default():
    """Test that regular classes have empty __type_params__."""
    class RegularClass:
        pass

    assert RegularClass.__type_params__ == ()


def test_type_params_settable():
    """Test that __type_params__ can be set to a tuple."""
    def f():
        pass

    # Setting to a tuple should work
    f.__type_params__ = (int, str)
    assert f.__type_params__ == (int, str)


def test_type_params_type_error():
    """Test that __type_params__ raises TypeError for non-tuple."""
    def f():
        pass

    try:
        f.__type_params__ = [1, 2, 3]  # list, not tuple
        assert False, "Should have raised TypeError"
    except TypeError:
        pass
