import pytest

def test_delete_attrs():
    # for whatever reason CPython raises TypeError instead of AttributeError
    # here
    for attr in ["__cause__", "__context__", "args", "__traceback__", "__suppress_context__"]:
        with pytest.raises(TypeError) as info:
            delattr(Exception(), attr)
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

def xtest_str_repr():
    assert str(ExceptionGroup("abc", [ValueError()])) == "abc (1 sub-exception)"
    assert str(ExceptionGroup("abc", [ValueError(), TypeError()])) == "abc (2 sub-exceptions)"
    assert repr(ExceptionGroup("abc", [ValueError(), TypeError()])) == "ExceptionGroup('abc', [ValueError(), TypeError()])"
    assert repr(ExceptionGroup("abc", [ValueError()])) == "ExceptionGroup('abc', [ValueError()])"

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

