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

    type CallableT[**P] = Callable[P, int]
    P = CallableT.__type_params__[0]
    assert P.__name__ == 'P'
    assert hasattr(P, 'args')
    assert hasattr(P, 'kwargs')

    type TupleT[*Ts] = tuple[*Ts]
    Ts = TupleT.__type_params__[0]
    assert Ts.__name__ == 'Ts'

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

    type Starred[U: (*T.__constraints__, float)] = U
    U = Starred.__type_params__[0]
    assert U.__constraints__ == (int, str, float)

# === Generic function tests ===

def test_generic_function():
    def identity[T](x: T) -> T:
        return x

    assert hasattr(identity, '__type_params__')
    assert len(identity.__type_params__) == 1
    assert identity.__type_params__[0].__name__ == 'T'
    assert identity.__qualname__ == 'test_generic_function.<locals>.identity'


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
    assert Stack.__qualname__ == 'test_generic_class.<locals>.Stack'


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
    # TODO: Fix error messages to be specific to annotation scope kinds
    # Walrus operator not allowed
    exc = raises(SyntaxError, exec, "type X = (y := 1)")
    assert str(exc.value).startswith("named expression cannot be used within")

    exc = raises(SyntaxError, exec, "type X = (yield 1)")
    assert str(exc.value).startswith("yield expression cannot be used within")

    exc = raises(SyntaxError, exec, "type X = (await 1)")
    assert str(exc.value).startswith("await expression cannot be used within")


# === TypeAliasType class tests ===

def test_type_alias_type_creation():
    from typing import TypeAliasType
    alias = TypeAliasType('MyType', int)
    assert alias.__name__ == 'MyType'
    assert alias.__value__ is int
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

def test_function_type_params():
    def f():
        pass
    assert f.__type_params__ == ()

    f.__type_params__ = (int, str)
    assert f.__type_params__ == (int, str)

    raises(TypeError, setattr, f, '__type_params__', [1, 2, 3])


def test_class_type_params():
    class RegularClass:
        pass
    assert RegularClass.__type_params__ == ()


# === Edge cases ===

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
    assert Container.__qualname__ == 'test_generic_method_inside_generic_class.<locals>.Container'
    assert Container.transform.__qualname__ == 'test_generic_method_inside_generic_class.<locals>.Container.transform'

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
    assert Outer.__qualname__ == 'test_nested_generic_classes.<locals>.Outer'
    assert Outer.Inner.__qualname__ == 'test_nested_generic_classes.<locals>.Outer.Inner'


# === Class namespace access tests (__classdict__) ===

def test_class_namespace_access():
    """Annotation scopes can access enclosing class namespace."""
    from typing import Callable

    # Type alias value
    class C1:
        Inner = list
        type Alias = Inner[int]
    assert C1.Alias.__value__ == list[int]

    # TypeVar bound
    class C2:
        Base = int
        type Alias[T: Base] = T
    assert C2.Alias.__type_params__[0].__bound__ is int

    # TypeVar constraints
    class C3:
        A, B = int, str
        type Alias[T: (A, B)] = T
    assert C3.Alias.__type_params__[0].__constraints__ == (int, str)

    # Generic class
    class C4:
        Base = int
        class Generic[T: Base]: pass
    assert C4.Generic.__type_params__[0].__bound__ is int

    # Generic function
    class C5:
        Base = int
        def method[T: Base](self, x: T) -> T: return x
    assert C5.method.__type_params__[0].__bound__ is int

    # Multiple type params with bounds, constraints, and mixed kinds
    class C6:
        A, B, C = int, str, float
        type Alias[T: A, U: (B, C), **P, *Ts] = tuple[T, U, Callable[P, T], *Ts]
    T, U, P, Ts = C6.Alias.__type_params__
    assert T.__bound__ is int
    assert U.__constraints__ == (str, float)
    assert P.__name__ == 'P'
    assert Ts.__name__ == 'Ts'

    # Later type param can reference earlier one
    class C7:
        Base = int
        type Alias[T: Base, U: T] = tuple[T, U]
    T, U = C7.Alias.__type_params__
    assert T.__bound__ is int
    assert U.__bound__ is T


def test_nested_class_namespace_isolation():
    """Class namespaces don't chain - only the immediate enclosing class is visible."""
    # Inner class cannot see outer class namespace
    class Outer:
        OuterOnly = int
        class Inner:
            type Alias[T: OuterOnly] = T
    T = Outer.Inner.Alias.__type_params__[0]
    raises(NameError, getattr, T, '__bound__')

    # Each nested class sees only its own namespace
    class A:
        X = "A"
        class B:
            X = "B"
            class C:
                X = "C"
                type Alias[T: X] = T
    assert A.B.C.Alias.__type_params__[0].__bound__ == "C"


def test_class_namespace_shadowing():
    """Class namespace shadows globals, enclosing functions, and type params."""
    # Shadows global
    global GlobalX
    GlobalX = "global"
    class C1:
        GlobalX = "class"
        type Alias[T: GlobalX] = T
    assert C1.Alias.__type_params__[0].__bound__ == "class"

    # Shadows enclosing function
    def outer():
        X = "function"
        class Inner:
            X = "class"
            type Alias[T: X] = T
        return Inner
    assert outer().Alias.__type_params__[0].__bound__ == "class"

    # Shadows type param in value (but not in bound)
    class C2:
        T = int
        type Alias[T: str] = list[T]  # value T resolves to class-level int
    assert C2.Alias.__type_params__[0].__bound__ is str
    assert C2.Alias.__value__ == list[int]


def test_function_scope_and_class_namespace():
    """Function scope interaction with class namespace access."""
    # Free variables from enclosing function are accessible
    def make_class():
        FuncLocal = int
        class Inner:
            type Alias[T: FuncLocal] = T
        return Inner
    assert make_class().Alias.__type_params__[0].__bound__ is int

    # But a function between class and annotation scope breaks class access
    class Outer:
        X = int
        def method(self):
            type InnerAlias[T: X] = T
            return InnerAlias
    alias = Outer().method()
    raises(NameError, getattr, alias.__type_params__[0], '__bound__')


def test_class_conditionally_bound_name_with_enclosing_function():
    """Class-bound names resolve to global in annotation scopes, not via closure.

    When a name is conditionally defined in a class (e.g., inside an if block),
    the symtable sees it as bound in the class. However, annotation scopes
    cannot see class-bound names via normal closure - they resolve to module globals.

    This test would fail if the name was incorrectly classified as FREE
    (would get "function" from closure) instead of GLOBAL_IMPLICIT (gets module global).

    See gh-109118.
    """
    globs = {"__name__": __name__}
    exec("""
x = "global"

def outer():
    x = "function"  # Variable in enclosing function (shadows global)

    class C:
        if False:
            x = "class"  # Conditionally bound - never assigned at runtime
        type Alias = x

    return C

C = outer()
# With correct classification (GLOBAL_IMPLICIT): resolves to module-level "global"
# With incorrect classification (FREE): would resolve to "function" from closure
assert C.Alias.__value__ == "global", f"Expected 'global', got {C.Alias.__value__!r}"
""", globs)


# === Generic class base tests ===

def test_generic_class_bases():
    """PEP 695 generic classes automatically inherit from typing.Generic."""
    from typing import Generic

    # Basic case: no explicit bases
    class C[T]: pass
    assert C.__bases__ == (Generic,)
    T, = C.__type_params__
    assert C.__orig_bases__ == (Generic[T],)

    # With explicit base
    class Base: pass
    class D[T](Base): pass
    assert D.__bases__ == (Base, Generic)
    T, = D.__type_params__
    assert D.__orig_bases__ == (Base, Generic[T])

    # Multiple type params
    class Multi[T, U, V]: pass
    T, U, V = Multi.__type_params__
    assert Multi.__orig_bases__ == (Generic[T, U, V],)


def test_generic_class_duplicate_generic_error():
    """Explicit Generic[T] with PEP 695 syntax raises TypeError."""
    from typing import Generic
    with raises(TypeError) as excinfo:
        class ClassA[T](Generic[T]): ...
    assert str(excinfo.value) == "Cannot inherit from Generic[...] multiple times."
