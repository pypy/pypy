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
    from typing import TypeAliasType
    alias = TypeAliasType('MyType', int)
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
    """Class namespace access via __classdict__ cell (PEP 695)."""
    class Outer:
        BaseType = int
        type Alias[T: BaseType] = list[T]

    # Accessing the bound should work - annotation scope can access class namespace
    T = Outer.Alias.__type_params__[0]
    assert T.__bound__ is int


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


# === Class namespace access tests (__classdict__) ===

def test_class_namespace_in_type_alias_value():
    """Type alias value can access class namespace."""
    class Container:
        Inner = list
        type Alias = Inner[int]
    assert Container.Alias.__value__ == list[int]


def test_class_namespace_with_constraints():
    """TypeVar constraints can access class namespace."""
    class Container:
        A = int
        B = str
        type Alias[T: (A, B)] = T
    T = Container.Alias.__type_params__[0]
    assert T.__constraints__ == (int, str)


def test_generic_class_with_class_bound():
    """Generic class type params can access class namespace."""
    class Container:
        BaseType = int
        class Generic[T: BaseType]:
            pass
    T = Container.Generic.__type_params__[0]
    assert T.__bound__ is int


def test_generic_function_in_class_with_class_bound():
    """Generic function type params can access enclosing class namespace."""
    class Container:
        BaseType = int
        def method[T: BaseType](self, x: T) -> T:
            return x
    T = Container.method.__type_params__[0]
    assert T.__bound__ is int


def test_function_breaks_class_namespace_chain():
    """A regular function between class and annotation scope breaks class access.

    This matches CPython behavior: class namespace is only accessible from
    annotation scopes directly nested in the class, not through intermediate
    functions.
    """
    class Outer:
        X = int
        def method(self):
            # Type alias inside method cannot see Outer.X
            type InnerAlias[T: X] = T  # noqa: F821
            return InnerAlias

    # Creating the type alias works, but accessing bound raises NameError
    outer = Outer()
    alias = outer.method()
    T = alias.__type_params__[0]
    raises(NameError, getattr, T, '__bound__')


def test_nested_class_sees_own_namespace():
    """Inner class annotation scope sees inner class namespace, not outer."""
    class Outer:
        X = "outer"
        class Inner:
            X = "inner"
            type Alias[T: X] = T

    T = Outer.Inner.Alias.__type_params__[0]
    assert T.__bound__ == "inner"


def test_nested_class_cannot_see_outer_class_namespace():
    """Inner class annotation scope cannot access outer class namespace.

    Class namespaces don't chain - only the immediately enclosing class
    is accessible.
    """
    class Outer:
        OuterOnly = int
        class Inner:
            type Alias[T: OuterOnly] = T  # noqa: F821

    T = Outer.Inner.Alias.__type_params__[0]
    raises(NameError, getattr, T, '__bound__')


def test_deeply_nested_classes():
    """Each class level has its own independent namespace."""
    class A:
        X = "A"
        class B:
            X = "B"
            class C:
                X = "C"
                type Alias[T: X] = T

    T = A.B.C.Alias.__type_params__[0]
    assert T.__bound__ == "C"


def test_class_namespace_shadows_global():
    """Class namespace takes precedence over global namespace."""
    # Define global
    global GlobalX
    GlobalX = "global"

    class Container:
        GlobalX = "class"  # Shadows global
        type Alias[T: GlobalX] = T

    T = Container.Alias.__type_params__[0]
    assert T.__bound__ == "class"


def test_class_namespace_shadows_type_param_in_value():
    """Class namespace shadows type parameter in type alias value.

    Note: This is CPython's behavior - the class-level name takes precedence
    over the type parameter in the value expression. The bound still uses
    the type parameter correctly.
    """
    class Container:
        T = int  # Class-level T
        type Alias[T: str] = list[T]  # In the value, T resolves to int (class-level)

    T = Container.Alias.__type_params__[0]
    assert T.__bound__ is str  # Bound is str (type param bound)
    # The value uses class-level T = int, not the type parameter
    assert Container.Alias.__value__ == list[int]

    # When there's no naming conflict, it works as expected
    class Container2:
        T = int  # Class-level T
        type Alias[X: str] = list[X]  # X is the type param, no conflict

    X = Container2.Alias.__type_params__[0]
    assert X.__bound__ is str
    assert Container2.Alias.__value__ == list[X]


def test_free_variable_from_function_scope():
    """Free variables from enclosing function are accessible."""
    def outer():
        FuncLocal = int
        class Inner:
            type Alias[T: FuncLocal] = T
        return Inner

    Inner = outer()
    T = Inner.Alias.__type_params__[0]
    assert T.__bound__ is int


def test_class_shadows_enclosing_function():
    """Class namespace shadows enclosing function namespace."""
    def outer():
        X = "function"
        class Inner:
            X = "class"
            type Alias[T: X] = T
        return Inner

    Inner = outer()
    T = Inner.Alias.__type_params__[0]
    assert T.__bound__ == "class"


def test_multiple_type_params_with_class_bounds():
    """Multiple type parameters can all access class namespace."""
    class Container:
        A = int
        B = str
        C = float
        type Alias[T: A, U: B, V: C] = tuple[T, U, V]

    T, U, V = Container.Alias.__type_params__
    assert T.__bound__ is int
    assert U.__bound__ is str
    assert V.__bound__ is float


def test_type_param_references_earlier_type_param():
    """Later type parameter bound can reference earlier type parameter."""
    class Container:
        Base = int
        type Alias[T: Base, U: T] = tuple[T, U]

    T, U = Container.Alias.__type_params__
    assert T.__bound__ is int
    # U's bound is T (the type parameter object itself)
    assert U.__bound__ is T


def test_paramspec_in_class():
    """ParamSpec in class works (no bounds, but should not error)."""
    from typing import Callable
    class Container:
        type Alias[**P] = Callable[P, int]

    P = Container.Alias.__type_params__[0]
    assert P.__name__ == 'P'


def test_typevartuple_in_class():
    """TypeVarTuple in class works (no bounds, but should not error)."""
    class Container:
        type Alias[*Ts] = tuple[*Ts]

    Ts = Container.Alias.__type_params__[0]
    assert Ts.__name__ == 'Ts'


def test_mixed_type_params_in_class():
    """Mix of TypeVar, ParamSpec, TypeVarTuple with class namespace access."""
    from typing import Callable
    class Container:
        Base = int
        type Alias[T: Base, **P, *Ts] = tuple[T, Callable[P, T], *Ts]

    T, P, Ts = Container.Alias.__type_params__
    assert T.__bound__ is int
    assert P.__name__ == 'P'
    assert Ts.__name__ == 'Ts'


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
