from _pypy_exceptiongroups import \
    BaseExceptionGroup, ExceptionGroup, \
    _collect_eg_leafs, _exception_group_projection, \
    _prep_reraise_star

import pytest


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


### helper function tests

def test_eg_leafs_basic():
    t1, v1 = TypeError(), ValueError()
    exceptions = [t1, v1]
    message = "42"
    excgroup = ExceptionGroup(message, exceptions)
    resultset = set()
    _collect_eg_leafs(excgroup, resultset)
    assert {t1, v1} == resultset

def test_eg_leafs_null():
    resultset = set()
    _collect_eg_leafs(None, resultset)
    assert not resultset

def test_eg_leafs_nogroup():
    exc = TypeError()
    resultset = set()
    _collect_eg_leafs(exc, resultset)
    assert resultset == {exc}

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
    resultset = set()
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

# TODO: Duplicates in eg?


