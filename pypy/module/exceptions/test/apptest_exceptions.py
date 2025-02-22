import pytest
import sys

def test_delete_attrs():
    # for whatever reason CPython raises TypeError instead of AttributeError
    # here
    for attr in ["__cause__", "__context__", "args", "__traceback__", "__suppress_context__"]:
        with pytest.raises(TypeError) as info:
            delattr(Exception(), attr)
        if sys.implementation.name != 'pypy' and attr in ("__suppress_context__",):
            assert str(info.value).endswith("can't delete numeric/char attribute")
        else:
            assert str(info.value).endswith("may not be deleted")

def test_notes():
    base = BaseException()
    base.add_note('test note')
    assert base.__notes__ == ['test note']
    base.add_note('second note')
    assert base.__notes__ == ['test note', 'second note']
    with pytest.raises(TypeError):
        base.add_note(42)
    assert base.__notes__ == ['test note', 'second note']

    e = Exception()
    e.__notes__ = 12
    with pytest.raises(TypeError):
        e.add_note('abc')

def test_importerror_kwarg_error():
    if sys.implementation.name == 'pypy':
        msg = "ImportError.__init__() got an unexpected keyword argument 'invalid'"
    else:
        msg = "'invalid' is an invalid keyword argument for ImportError()"
    exc = raises(TypeError,
                 ImportError,
                 'test', invalid='keyword', another=True)
    assert str(exc.value) == "ImportError.__init__() got 2 unexpected keyword arguments"

    exc = raises(TypeError, ImportError, 'test', invalid='keyword')
    assert str(exc.value) == msg

    exc = raises(TypeError,
                 ImportError,
                 'test', name='name', invalid='keyword')
    assert str(exc.value) == msg

    exc = raises(TypeError,
                 ImportError,
                 'test', path='path', invalid='keyword')
    assert str(exc.value) == msg



# ExceptionGroup tests

def test_exception_group():
    # the actual tests are in extra_tests, this is a simple smoke test that the
    # integration into builtins works
    assert issubclass(ExceptionGroup, BaseExceptionGroup)

def test_exceptiongroup_instantiate():
    t1, v1 = TypeError(), ValueError()
    exceptions = [t1, v1]
    message = "42"
    excgroup = ExceptionGroup(message, exceptions)
    assert excgroup.message == message
    assert excgroup.exceptions == tuple(exceptions)

def test_exceptiongroup_instantiate_check_message():
    t1, v1 = TypeError(), ValueError()
    exceptions = [t1, v1]
    with pytest.raises(TypeError) as e:
        ExceptionGroup(42, exceptions)
    with pytest.raises(TypeError) as e:
        ExceptionGroup(KeyError(), exceptions)
    with pytest.raises(TypeError) as e:
        ExceptionGroup(exceptions, exceptions)

def test_exceptiongroup_instantiate_check_exceptions():
    message = "bla bla bla"
    with pytest.raises(TypeError) as e:
        ExceptionGroup(message, ValueError(42))
    with pytest.raises(TypeError) as e:
        ExceptionGroup(message, {ValueError(42)})
    with pytest.raises(ValueError) as e:
        ExceptionGroup(message, [])
    with pytest.raises(ValueError) as e:
        ExceptionGroup(message, (ValueError(42), 42))

def test_fields_are_readonly():
    eg = ExceptionGroup("eg", [TypeError(1), OSError(2)])
    assert type(eg.exceptions) == tuple
    eg.message
    with pytest.raises(AttributeError):
        eg.message = "new msg"
    eg.exceptions
    with pytest.raises(AttributeError):
        eg.exceptions = [OSError("xyz")]

# NOTE: The empty lines in here are important for
#       test_basics_exceptiongroup_fields
def h_create_simple_eg():
    excs = []
    try:
        try:
            raise MemoryError("context and cause for ValueError(1)")
        except MemoryError as e:
            raise ValueError(1) from e
    except ValueError as e:
        excs.append(e)

    try:
        try:
            raise OSError("context for TypeError")
        except OSError:
            raise TypeError(int)
    except TypeError as e:
        excs.append(e)

    try:
        try:
            raise ImportError("context for ValueError(2)")
        except ImportError:
            raise ValueError(2)
    except ValueError as e:
        excs.append(e)

    try:
        raise ExceptionGroup("simple eg", excs)
    except ExceptionGroup as e:
        return e

def test_basics_exceptiongroup_fields():
    eg = h_create_simple_eg()

    # check msg
    assert eg.message == "simple eg"
    assert eg.args[0] == "simple eg"

    # check cause and context
    assert isinstance(eg.exceptions[0], ValueError)
    assert isinstance(eg.exceptions[0].__cause__, MemoryError)
    assert isinstance(eg.exceptions[0].__context__, MemoryError)
    assert isinstance(eg.exceptions[1], TypeError)
    assert eg.exceptions[1].__cause__ == None
    assert isinstance(eg.exceptions[1].__context__, OSError)
    assert isinstance(eg.exceptions[2], ValueError)
    assert eg.exceptions[2].__cause__ == None
    assert isinstance(eg.exceptions[2].__context__, ImportError)

    # check tracebacks
    line0 = h_create_simple_eg.__code__.co_firstlineno
    tb_linenos = [line0 + 27, [line0 + 6, line0 + 14, line0 + 22]]
    assert eg.__traceback__.tb_lineno == tb_linenos[0]
    assert eg.__traceback__.tb_next == None
    for i in range(3):
        tb = eg.exceptions[i].__traceback__
        assert tb.tb_next == None
        assert tb.tb_lineno == tb_linenos[1][i]

def test_notes_is_list_of_strings_if_it_exists():
    eg = h_create_simple_eg()
    note = "This is a happy note for the exception group"
    assert not hasattr(eg, "__notes__")
    eg.add_note(note)
    assert eg.__notes__ == [note]

def test_exceptiongroup_wraps_BaseException__raises_TypeError():
    with pytest.raises(TypeError):
        ExceptionGroup("eg", [ValueError(1), KeyboardInterrupt(2)])

def test_exceptiongroup_subclass_wraps_non_base_exceptions():
    class MyEG(ExceptionGroup):
        pass
    assert type(MyEG("eg", [ValueError(12), TypeError(42)])) == MyEG

def test_exceptiongroup_inheritance_hierarchy():
    assert issubclass(BaseExceptionGroup, BaseException)
    assert issubclass(ExceptionGroup, BaseExceptionGroup)
    assert issubclass(ExceptionGroup, Exception)

def test_baseexceptiongroup_instantiate():
    # a BaseExceptionGroup instantiation will magically
    # return an ExceptionGroup, if all of the exceptions
    # are instances of Exception.
    excgroup = BaseExceptionGroup('1', [ValueError()])
    assert type(excgroup) is ExceptionGroup
    # KeyboardInterrupt inherits from BaseException, not Exception
    excgroup = BaseExceptionGroup('1', [ValueError(), KeyboardInterrupt()])
    assert type(excgroup) is BaseExceptionGroup

def test_str_repr():
    assert str(ExceptionGroup("abc", [ValueError()])) == "abc (1 sub-exception)"
    assert str(ExceptionGroup("abc", [ValueError(), TypeError()])) == "abc (2 sub-exceptions)"
    assert repr(ExceptionGroup("abc", [ValueError(), TypeError()])) == "ExceptionGroup('abc', [ValueError(), TypeError()])"
    assert repr(ExceptionGroup("abc", [ValueError()])) == "ExceptionGroup('abc', [ValueError()])"

def h_create_nested_eg():
    excs = []
    try:
        try:
            raise TypeError(bytes)
        except TypeError as e:
            raise ExceptionGroup("nested", [e])
    except ExceptionGroup as e:
        excs.append(e)

    try:
        try:
            raise MemoryError("out of memory")
        except MemoryError as e:
            raise ValueError(1) from e
    except ValueError as e:
        excs.append(e)

    try:
        raise ExceptionGroup("root", excs)
    except ExceptionGroup as eg:
        return eg

def h_leaf_generator(exc, tbs=None):
    if tbs is None:
        tbs = []
    tbs.append(exc.__traceback__)
    if isinstance(exc, BaseExceptionGroup):
        for e in exc.exceptions:
            yield from h_leaf_generator(e, tbs)
    else:
        # exc is a leaf exception and its traceback
        # is the concatenation of the traceback
        # segments in tbs
        yield exc, tbs
    tbs.pop()

def test_nested_exception_group_tracebacks():
    eg = h_create_nested_eg()

    line0 = h_create_nested_eg.__code__.co_firstlineno
    for tb, expected in [
        (eg.__traceback__, line0 + 19),
        (eg.exceptions[0].__traceback__, line0 + 6),
        (eg.exceptions[1].__traceback__, line0 + 14),
        (eg.exceptions[0].exceptions[0].__traceback__, line0 + 4),
    ]:
        assert tb.tb_lineno == expected
        assert tb.tb_next == None

def test_nested_exception_group_subgroup_tracebacks_preserved():
    eg_r = h_create_nested_eg()
    eg = eg_r.subgroup((TypeError, ValueError))

    line0 = h_create_nested_eg.__code__.co_firstlineno
    for tb, expected in [
        (eg.__traceback__, line0 + 19),
        (eg.exceptions[0].__traceback__, line0 + 6),
        (eg.exceptions[0].exceptions[0].__traceback__, line0 + 4),
    ]:
        assert tb.tb_lineno == expected
        assert tb.tb_next == None

def test_iteration_full_tracebacks():
    eg = h_create_nested_eg()
    # check that iteration over leaves
    # produces the expected tracebacks
    assert len(list(h_leaf_generator(eg))) == 2

    line0 = h_create_nested_eg.__code__.co_firstlineno
    expected_tbs = [[line0 + 19, line0 + 6, line0 + 4], [line0 + 19, line0 + 14]]

    for i, (_, tbs) in enumerate(h_leaf_generator(eg)):
        assert [tb.tb_lineno for tb in tbs] == expected_tbs[i]


def test_attribute_error_from_getattr_has_name_and_object():
    class A:
        def __getattr__(self, name):
            raise AttributeError('nope')
    a = A()
    with raises(AttributeError) as info:
        a.abc
    assert info.value.name == 'abc'
    assert info.value.obj is a

    class A:
        def __getattr__(self, name):
            return getattr(list, name + 'nd')
    a = A()
    with raises(AttributeError) as info:
        a.app
    assert info.value.name == 'appnd'
    assert info.value.obj is list

# TODO: Duplicates in eg?


def test_subgroup_invalid_args():
    eg = ExceptionGroup("abc", [ValueError(), TypeError()])
    with pytest.raises(TypeError):
        eg.subgroup(42)
    with pytest.raises(TypeError):
        eg.subgroup(ValueError())
    with pytest.raises(TypeError):
        eg.subgroup(int)
    with pytest.raises(TypeError):
        eg.subgroup(eg)
    with pytest.raises(TypeError):
        eg.subgroup({TypeError, ValueError})
    with pytest.raises(TypeError):
        eg.subgroup([TypeError, ValueError])
    with pytest.raises(TypeError):
        eg.subgroup([TypeError, 42, ValueError])

def test_subgroup_bytype_single_simple():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    eg = ExceptionGroup("def", [typ2])
    assert repr(eg.subgroup(TypeError)) == "ExceptionGroup('def', [TypeError()])"
    assert repr(eg.subgroup(ValueError)) == "None"
    eg = ExceptionGroup("abc", [val1, typ1])
    assert repr(eg.subgroup(TypeError)) == "ExceptionGroup('abc', [TypeError()])"
    assert repr(eg.subgroup(ValueError)) == "ExceptionGroup('abc', [ValueError(1)])"
    eg = ExceptionGroup("abc", [val1, typ1, val2, val3])
    assert repr(eg.subgroup(TypeError)) == "ExceptionGroup('abc', [TypeError()])"
    assert repr(eg.subgroup(ValueError)) == "ExceptionGroup('abc', [ValueError(1), ValueError(2), ValueError(3)])"
    assert repr(eg.subgroup(BaseExceptionGroup)) == "ExceptionGroup('abc', [ValueError(1), TypeError(), ValueError(2), ValueError(3)])"
    assert repr(eg.subgroup(ExceptionGroup)) == "ExceptionGroup('abc', [ValueError(1), TypeError(), ValueError(2), ValueError(3)])"

def test_subgroup_bytype_single_nested():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    key1 = KeyError()
    div1 = ZeroDivisionError()
    eg = ExceptionGroup("abc", [key1, val1, ExceptionGroup("def", [val2, val3, typ2, div1]), typ1])
    assert repr(eg.subgroup(ValueError)) == "ExceptionGroup('abc', [ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3)])])"
    assert repr(eg.subgroup(TypeError)) == "ExceptionGroup('abc', [ExceptionGroup('def', [TypeError()]), TypeError()])"
    assert repr(eg.subgroup(KeyError)) == "ExceptionGroup('abc', [KeyError()])"
    assert repr(eg.subgroup(ZeroDivisionError)) == "ExceptionGroup('abc', [ExceptionGroup('def', [ZeroDivisionError()])])"
    assert repr(eg.subgroup(BaseExceptionGroup)) == "ExceptionGroup('abc', [KeyError(), ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3), TypeError(), ZeroDivisionError()]), TypeError()])"
    assert repr(eg.subgroup(ExceptionGroup)) == "ExceptionGroup('abc', [KeyError(), ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3), TypeError(), ZeroDivisionError()]), TypeError()])"

def test_subgroup_bytype_multi_simple():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    eg = ExceptionGroup("def", [typ2])
    assert repr(eg.subgroup((TypeError, ValueError))) == "ExceptionGroup('def', [TypeError()])"
    assert repr(eg.subgroup((ValueError, TypeError))) == "ExceptionGroup('def', [TypeError()])"
    eg = ExceptionGroup("abc", [val1, typ1])
    assert repr(eg.subgroup((ValueError, TypeError))) == "ExceptionGroup('abc', [ValueError(1), TypeError()])"
    assert repr(eg.subgroup((TypeError, ValueError))) == "ExceptionGroup('abc', [ValueError(1), TypeError()])"
    eg = ExceptionGroup("abc", [val1, typ1, val2, val3])
    assert repr(eg.subgroup(TypeError)) == "ExceptionGroup('abc', [TypeError()])"
    assert repr(eg.subgroup(ValueError)) == "ExceptionGroup('abc', [ValueError(1), ValueError(2), ValueError(3)])"
    assert eg.subgroup(tuple([])) == None

def test_subgroup_bytype_multi_nested():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    key1 = KeyError()
    div1 = ZeroDivisionError()
    eg = ExceptionGroup("abc", [key1, val1, ExceptionGroup("def", [val2, val3, typ2, div1]), typ1])
    assert repr(eg.subgroup((ValueError, TypeError))) == "ExceptionGroup('abc', [ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3), TypeError()]), TypeError()])"
    assert repr(eg.subgroup((KeyError, KeyError))) == "ExceptionGroup('abc', [KeyError()])"
    assert eg.subgroup(tuple([])) == None


def test_subgroup_bypredicate_passthrough():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    key1 = KeyError()
    div1 = ZeroDivisionError()
    eg = ExceptionGroup("abc", [key1, val1, ExceptionGroup("def", [val2, val3, typ2, div1]), typ1])
    assert eg is eg.subgroup(lambda e: True)

def test_subgroup_bypredicate_no_match():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    key1 = KeyError()
    div1 = ZeroDivisionError()
    eg = ExceptionGroup("abc", [key1, val1, ExceptionGroup("def", [val2, val3, typ2, div1]), typ1])
    assert eg.subgroup(lambda e: False) == None

def test_subgroup_bypredicate_nested():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    key1 = KeyError()
    div1 = ZeroDivisionError()
    eg = ExceptionGroup("abc", [key1, val1, ExceptionGroup("def", [val2, val3, typ2, div1]), typ1])
    assert repr(eg.subgroup(lambda e: isinstance(e, ValueError) and e.args[0] < 3)) \
        == "ExceptionGroup('abc', [ValueError(1), ExceptionGroup('def', [ValueError(2)])])"

def test_subgroup_bytype_is_id_if_all_subexceptions_match_and_split_is_not():
    # NOTE: This is why split and subgroup are different
    typ2 = TypeError()
    eg = ExceptionGroup("def", [typ2])
    eg_subgroup = eg.subgroup(TypeError)
    eg_split = eg.split(TypeError)[0]
    assert repr(eg_subgroup) == repr(eg_split)
    if sys.implementation.name == 'pypy':
        assert eg_subgroup is eg
    assert not eg_split is eg

def test_split_bytype_single_simple():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    eg = ExceptionGroup("def", [typ2])
    assert repr(eg.split(TypeError)) == "(ExceptionGroup('def', [TypeError()]), None)"
    assert repr(eg.split(ValueError)) == "(None, ExceptionGroup('def', [TypeError()]))"
    eg = ExceptionGroup("abc", [val1, typ1])
    assert repr(eg.split(TypeError)) == "(ExceptionGroup('abc', [TypeError()]), ExceptionGroup('abc', [ValueError(1)]))"
    assert repr(eg.split(ValueError)) == "(ExceptionGroup('abc', [ValueError(1)]), ExceptionGroup('abc', [TypeError()]))"
    eg = ExceptionGroup("abc", [val1, typ1, val2, val3])
    assert repr(eg.split(TypeError)) == "(ExceptionGroup('abc', [TypeError()]), ExceptionGroup('abc', [ValueError(1), ValueError(2), ValueError(3)]))"
    assert repr(eg.split(ValueError)) == "(ExceptionGroup('abc', [ValueError(1), ValueError(2), ValueError(3)]), ExceptionGroup('abc', [TypeError()]))"
    assert repr(eg.split(BaseExceptionGroup)) == "(ExceptionGroup('abc', [ValueError(1), TypeError(), ValueError(2), ValueError(3)]), None)"
    assert repr(eg.split(ExceptionGroup)) == "(ExceptionGroup('abc', [ValueError(1), TypeError(), ValueError(2), ValueError(3)]), None)"

def test_split_bytype_single_nested():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    key1 = KeyError()
    div1 = ZeroDivisionError()
    eg = ExceptionGroup("abc", [key1, val1, ExceptionGroup("def", [val2, val3, typ2, div1]), typ1])
    assert repr(eg.split(ValueError)) == "(ExceptionGroup('abc', [ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3)])]), ExceptionGroup('abc', [KeyError(), ExceptionGroup('def', [TypeError(), ZeroDivisionError()]), TypeError()]))"
    assert repr(eg.split(TypeError)) == "(ExceptionGroup('abc', [ExceptionGroup('def', [TypeError()]), TypeError()]), ExceptionGroup('abc', [KeyError(), ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3), ZeroDivisionError()])]))"
    assert repr(eg.split(KeyError)) == "(ExceptionGroup('abc', [KeyError()]), ExceptionGroup('abc', [ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3), TypeError(), ZeroDivisionError()]), TypeError()]))"
    assert repr(eg.split(ZeroDivisionError)) == "(ExceptionGroup('abc', [ExceptionGroup('def', [ZeroDivisionError()])]), ExceptionGroup('abc', [KeyError(), ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3), TypeError()]), TypeError()]))"
    assert repr(eg.split(BaseExceptionGroup)) == "(ExceptionGroup('abc', [KeyError(), ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3), TypeError(), ZeroDivisionError()]), TypeError()]), None)"
    assert repr(eg.split(ExceptionGroup)) == "(ExceptionGroup('abc', [KeyError(), ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3), TypeError(), ZeroDivisionError()]), TypeError()]), None)"

def test_split_bytype_multi_simple():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    eg = ExceptionGroup("def", [typ2])
    assert repr(eg.split((TypeError, ValueError))) == "(ExceptionGroup('def', [TypeError()]), None)"
    assert repr(eg.split((ValueError, TypeError))) == "(ExceptionGroup('def', [TypeError()]), None)"
    eg = ExceptionGroup("abc", [val1, typ1])
    assert repr(eg.split((ValueError, TypeError))) == "(ExceptionGroup('abc', [ValueError(1), TypeError()]), None)"
    assert repr(eg.split((TypeError, ValueError))) == "(ExceptionGroup('abc', [ValueError(1), TypeError()]), None)"
    eg = ExceptionGroup("abc", [val1, typ1, val2, val3])
    assert repr(eg.split(TypeError)) == "(ExceptionGroup('abc', [TypeError()]), ExceptionGroup('abc', [ValueError(1), ValueError(2), ValueError(3)]))"
    assert repr(eg.split(ValueError)) == "(ExceptionGroup('abc', [ValueError(1), ValueError(2), ValueError(3)]), ExceptionGroup('abc', [TypeError()]))"
    assert repr(eg.split(tuple([]))) == "(None, ExceptionGroup('abc', [ValueError(1), TypeError(), ValueError(2), ValueError(3)]))"

def test_split_bytype_multi_nested():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    key1 = KeyError()
    div1 = ZeroDivisionError()
    eg = ExceptionGroup("abc", [key1, val1, ExceptionGroup("def", [val2, val3, typ2, div1]), typ1])
    assert repr(eg.split((ValueError, TypeError))) == "(ExceptionGroup('abc', [ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3), TypeError()]), TypeError()]), ExceptionGroup('abc', [KeyError(), ExceptionGroup('def', [ZeroDivisionError()])]))"
    assert repr(eg.split((KeyError, KeyError))) == "(ExceptionGroup('abc', [KeyError()]), ExceptionGroup('abc', [ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3), TypeError(), ZeroDivisionError()]), TypeError()]))"
    assert repr(eg.split(tuple([]))) == "(None, ExceptionGroup('abc', [KeyError(), ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3), TypeError(), ZeroDivisionError()]), TypeError()]))"

def test_split_bypredicate_passthrough():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    key1 = KeyError()
    div1 = ZeroDivisionError()
    eg = ExceptionGroup("abc", [key1, val1, ExceptionGroup("def", [val2, val3, typ2, div1]), typ1])
    assert repr(eg.split(lambda e: True)) == "(ExceptionGroup('abc', [KeyError(), ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3), TypeError(), ZeroDivisionError()]), TypeError()]), None)"

def test_split_bypredicate_no_match():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    key1 = KeyError()
    div1 = ZeroDivisionError()
    eg = ExceptionGroup("abc", [key1, val1, ExceptionGroup("def", [val2, val3, typ2, div1]), typ1])
    assert repr(eg.split(lambda e: False)) == "(None, ExceptionGroup('abc', [KeyError(), ValueError(1), ExceptionGroup('def', [ValueError(2), ValueError(3), TypeError(), ZeroDivisionError()]), TypeError()]))"

def test_split_bypredicate_nested():
    val1 = ValueError(1)
    typ1 = TypeError()
    val2 = ValueError(2)
    val3 = ValueError(3)
    typ2 = TypeError()
    key1 = KeyError()
    div1 = ZeroDivisionError()
    eg = ExceptionGroup("abc", [key1, val1, ExceptionGroup("def", [val2, val3, typ2, div1]), typ1])
    assert repr(eg.split(lambda e: isinstance(e, ValueError) and e.args[0] < 3)) \
        == "(ExceptionGroup('abc', [ValueError(1), ExceptionGroup('def', [ValueError(2)])]), ExceptionGroup('abc', [KeyError(), ExceptionGroup('def', [ValueError(3), TypeError(), ZeroDivisionError()]), TypeError()]))"

def h_make_deep_eg():
    e = TypeError(1)
    for _ in range(2000):
        e = ExceptionGroup("eg", [e])
    return e

def test_deep_split():
    e = h_make_deep_eg()
    with pytest.raises(RecursionError):
        e.split(TypeError)

def test_deep_subgroup():
    e = h_make_deep_eg()
    with pytest.raises(RecursionError):
        e.subgroup(TypeError)

def test_subgroup_copies_cause_etc():
    e = ExceptionGroup("23", [TypeError(), ValueError()])
    e.__notes__ = ['hello']
    se = e.subgroup(ValueError)
    assert e.__cause__ == se.__cause__
    assert e.__traceback__ == se.__traceback__
    assert e.__context__ == se.__context__
    assert e.__notes__ == se.__notes__

def test_derive_does_not_copies_cause_etc():
    e = ExceptionGroup("23", [TypeError(), ValueError()])
    e.__notes__ = ['hello']
    se = e.derive([IndexError()])
    assert se.__cause__ is None
    assert se.__traceback__ is None
    assert se.__context__ is None
    assert not hasattr(se, '__notes__')

def test_derive_always_creates_exception_group():
    class MyEG(ExceptionGroup):
        pass
    eg = MyEG("abc", [ValueError(), TypeError()])
    eg2 = eg.derive([ValueError()])
    assert type(eg2) is ExceptionGroup

def test_init_called():
    # issue 5218
    initcalled = []

    class MyException(Exception):
        def __init__(self, message):
            initcalled.append(message)

    class MyExceptionGroup(ExceptionGroup, MyException):
        pass

    MyExceptionGroup("...", [Exception()])
    assert len(initcalled) == 0

# _prep_reraise_star tests

if sys.implementation.name == 'pypy':
    from __exceptions__ import _prep_reraise_star, _collect_eg_leafs, _exception_group_projection
    from __pypy__ import identity_dict

    def test_prep_reraise_star_simple():
        assert _prep_reraise_star(TypeError(), [None]) is None
        assert _prep_reraise_star(ExceptionGroup('abc', [ValueError(), TypeError()]), [None]) is None

        value = ValueError()
        res = _prep_reraise_star(ExceptionGroup('abc', [value, TypeError()]), [ExceptionGroup('abc', [value])])
        assert repr(res) == "ExceptionGroup('abc', [ValueError()])"
        assert res.exceptions[0] is value

    def test_prep_reraise_exception_happens_in_except_star():
        value = ValueError()
        full_eg = ExceptionGroup('abc', [value, TypeError()])
        value_eg = ExceptionGroup('abc', [value])
        try:
            raise Exception
        except Exception as e:
            tb1 = e.__traceback__
        try:
            raise Exception
        except Exception as e:
            tb2 = e.__traceback__
        full_eg.__traceback__ = tb1
        value_eg.__traceback__ = tb1
        zerodiv = ZeroDivisionError('division by zero')
        zerodiv.__traceback__ = tb2
        assert repr(_prep_reraise_star(full_eg, [zerodiv, value_eg])) == "ExceptionGroup('', [ZeroDivisionError('division by zero'), ExceptionGroup('abc', [ValueError()])])"

    # helper function tests

    def test_eg_leafs_basic():
        t1, v1 = TypeError(), ValueError()
        exceptions = [t1, v1]
        message = "42"
        excgroup = ExceptionGroup(message, exceptions)
        resultset = identity_dict()
        _collect_eg_leafs(excgroup, resultset)
        print(resultset.keys())
        assert t1 in resultset
        assert v1 in resultset

    def test_eg_leafs_null():
        resultset = identity_dict()
        _collect_eg_leafs(None, resultset)
        assert not resultset

    def test_eg_leafs_nogroup():
        exc = TypeError()
        resultset = identity_dict()
        _collect_eg_leafs(exc, resultset)
        assert exc in resultset

    def test_eg_leafs_recursive():
        # TODO: fix
        val1 = ValueError(1)
        typ1 = TypeError()
        val2 = ValueError(2)
        val3 = ValueError(3)
        typ2 = TypeError()
        key1 = KeyError()
        div1 = ZeroDivisionError()
        eg = ExceptionGroup("abc", [key1, val1, ExceptionGroup("def", [val2, val3, typ2, div1]), typ1])
        resultset = identity_dict()
        collected = _collect_eg_leafs(eg, resultset)
        assert len(resultset) == 7
        for e in [val1, typ1, val2, val3, typ2, key1, div1]:
            assert e in resultset

    def test_exception_group_projection_basic():
        val1 = ValueError(1)
        typ1 = TypeError()
        val2 = ValueError(2)
        val3 = ValueError(3)
        typ2 = TypeError()
        key1 = KeyError()
        div1 = ZeroDivisionError()
        eg = ExceptionGroup("abc", [key1, val1, ExceptionGroup("def", [val2, val3, typ2, div1]), typ1])
        keep1 = ExceptionGroup("meep", [key1, typ1])
        keep2 = ExceptionGroup("moop", [val2, ExceptionGroup("doop", [val3])])
        result = _exception_group_projection(eg, [keep1, keep2])
        assert repr(result) == \
            "ExceptionGroup('abc', [KeyError(), ExceptionGroup('def', [ValueError(2), ValueError(3)]), TypeError()])"

    def test_exception_group_projection_duplicated_in_keep():
        val1 = ValueError(1)
        typ1 = TypeError()
        val2 = ValueError(2)
        val3 = ValueError(3)
        typ2 = TypeError()
        key1 = KeyError()
        div1 = ZeroDivisionError()
        eg = ExceptionGroup("abc", [key1, val1, ExceptionGroup("def", [val2, val3, typ2, div1]), typ1])
        keep1 = ExceptionGroup("meep", [key1, typ1, val2])
        keep2 = ExceptionGroup("moop", [val2, ExceptionGroup("doop", [key1, val3])])
        result = _exception_group_projection(eg, [keep1, keep2])
        assert repr(result) == \
            "ExceptionGroup('abc', [KeyError(), ExceptionGroup('def', [ValueError(2), ValueError(3)]), TypeError()])"
