
CHECK_EG_MATCH
{
    PyObject *match_type = POP();
    if (check_except_star_type_valid(tstate, match_type) < 0)
    {
        Py_DECREF(match_type);
        goto error;
    }

    PyObject *exc_value = TOP();
    PyObject *match = NULL, *rest = NULL;
    int res = exception_group_match(exc_value, match_type,
                                    &match, &rest);
    Py_DECREF(match_type);
    if (res < 0)
    {
        goto error;
    }

    if (match == NULL || rest == NULL)
    {
        assert(match == NULL);
        assert(rest == NULL);
        goto error;
    }
    if (Py_IsNone(match))
    {
        PUSH(match);
        Py_XDECREF(rest);
    }
    else
    {
        /* Total or partial match - update the stack from
         * [val]
         * to
         * [rest, match]
         * (rest can be Py_None)
         */

        SET_TOP(rest);
        PUSH(match);
        PyErr_SetExcInfo(NULL, Py_NewRef(match), NULL);
        Py_DECREF(exc_value);
    }
    DISPATCH();
}

PREP_RERAISE_STAR
{
    PyObject *excs = POP();
    assert(PyList_Check(excs));
    PyObject *orig = POP();

    PyObject *val = _PyExc_PrepReraiseStar(orig, excs);
    Py_DECREF(excs);
    Py_DECREF(orig);

    if (val == NULL)
    {
        goto error;
    }

    PUSH(val);
    DISPATCH();
}

static int
check_except_star_type_valid(PyThreadState *tstate, PyObject *right)
{
    if (check_except_type_valid(tstate, right) < 0)
    {
        return -1;
    }

    /* reject except *ExceptionGroup */

    int is_subclass = 0;
    if (PyTuple_Check(right))
    {
        Py_ssize_t length = PyTuple_GET_SIZE(right);
        for (Py_ssize_t i = 0; i < length; i++)
        {
            PyObject *exc = PyTuple_GET_ITEM(right, i);
            is_subclass = PyObject_IsSubclass(exc, PyExc_BaseExceptionGroup);
            if (is_subclass < 0)
            {
                return -1;
            }
            if (is_subclass)
            {
                break;
            }
        }
    }
    else
    {
        is_subclass = PyObject_IsSubclass(right, PyExc_BaseExceptionGroup);
        if (is_subclass < 0)
        {
            return -1;
        }
    }
    if (is_subclass)
    {
        _PyErr_SetString(tstate, PyExc_TypeError,
                         CANNOT_EXCEPT_STAR_EG);
        return -1;
    }
    return 0;
}

/* Logic for matching an exception in an except* clause (too
   complicated for inlining).
*/

static int
exception_group_match(PyObject *exc_value, PyObject *match_type,
                      PyObject **match, PyObject **rest)
{
    if (Py_IsNone(exc_value))
    {
        *match = Py_NewRef(Py_None);
        *rest = Py_NewRef(Py_None);
        return 0;
    }
    assert(PyExceptionInstance_Check(exc_value));

    if (PyErr_GivenExceptionMatches(exc_value, match_type))
    {
        /* Full match of exc itself */
        bool is_eg = _PyBaseExceptionGroup_Check(exc_value);
        if (is_eg)
        {
            *match = Py_NewRef(exc_value);
        }
        else
        {
            /* naked exception - wrap it */
            PyObject *excs = PyTuple_Pack(1, exc_value);
            if (excs == NULL)
            {
                return -1;
            }
            PyObject *wrapped = _PyExc_CreateExceptionGroup("", excs);
            Py_DECREF(excs);
            if (wrapped == NULL)
            {
                return -1;
            }
            *match = wrapped;
        }
        *rest = Py_NewRef(Py_None);
        return 0;
    }

    /* exc_value does not match match_type.
     * Check for partial match if it's an exception group.
     */
    if (_PyBaseExceptionGroup_Check(exc_value))
    {
        PyObject *pair = PyObject_CallMethod(exc_value, "split", "(O)",
                                             match_type);
        if (pair == NULL)
        {
            return -1;
        }
        assert(PyTuple_CheckExact(pair));
        assert(PyTuple_GET_SIZE(pair) == 2);
        *match = Py_NewRef(PyTuple_GET_ITEM(pair, 0));
        *rest = Py_NewRef(PyTuple_GET_ITEM(pair, 1));
        Py_DECREF(pair);
        return 0;
    }
    /* no match */
    *match = Py_NewRef(Py_None);
    *rest = Py_NewRef(Py_None);
    return 0;
}

/*
   This function is used by the interpreter to calculate
   the exception group to be raised at the end of a
   try-except* construct.

   orig: the original except that was caught.
   excs: a list of exceptions that were raised/reraised
         in the except* clauses.

   Calculates an exception group to raise. It contains
   all exceptions in excs, where those that were reraised
   have same nesting structure as in orig, and those that
   were raised (if any) are added as siblings in a new EG.

   Returns NULL and sets an exception on failure.
*/

PyObject *
_PyExc_PrepReraiseStar(PyObject *orig, PyObject *excs)
{
    assert(PyExceptionInstance_Check(orig));
    assert(PyList_Check(excs));

    Py_ssize_t numexcs = PyList_GET_SIZE(excs);

    if (numexcs == 0)
    {
        return Py_NewRef(Py_None);
    }

    if (!_PyBaseExceptionGroup_Check(orig))
    {
        /* a naked exception was caught and wrapped. Only one except* clause
         * could have executed,so there is at most one exception to raise.
         */

        assert(numexcs == 1 || (numexcs == 2 && PyList_GET_ITEM(excs, 1) == Py_None));

        PyObject *e = PyList_GET_ITEM(excs, 0);
        assert(e != NULL);
        return Py_NewRef(e);
    }

    PyObject *raised_list = PyList_New(0);
    if (raised_list == NULL)
    {
        return NULL;
    }
    PyObject *reraised_list = PyList_New(0);
    if (reraised_list == NULL)
    {
        Py_DECREF(raised_list);
        return NULL;
    }

    /* Now we are holding refs to raised_list and reraised_list */

    PyObject *result = NULL;

    /* Split excs into raised and reraised by comparing metadata with orig */
    for (Py_ssize_t i = 0; i < numexcs; i++)
    {
        PyObject *e = PyList_GET_ITEM(excs, i);
        assert(e != NULL);
        if (Py_IsNone(e))
        {
            continue;
        }
        bool is_reraise = is_same_exception_metadata(e, orig);
        PyObject *append_list = is_reraise ? reraised_list : raised_list;
        if (PyList_Append(append_list, e) < 0)
        {
            goto done; // TODO Was ist hiermit?
        }
    }

    PyObject *reraised_eg = exception_group_projection(orig, reraised_list);
    if (reraised_eg == NULL)
    {
        goto done;
    }

    if (!Py_IsNone(reraised_eg))
    {
        assert(is_same_exception_metadata(reraised_eg, orig));
    }
    Py_ssize_t num_raised = PyList_GET_SIZE(raised_list);
    if (num_raised == 0)
    {
        result = reraised_eg;
    }
    else if (num_raised > 0)
    {
        int res = 0;
        if (!Py_IsNone(reraised_eg))
        {
            res = PyList_Append(raised_list, reraised_eg);
        }
        Py_DECREF(reraised_eg);
        if (res < 0)
        {
            goto done;
        }
        if (PyList_GET_SIZE(raised_list) > 1)
        {
            result = _PyExc_CreateExceptionGroup("", raised_list);
        }
        else
        {
            result = Py_NewRef(PyList_GetItem(raised_list, 0));
        }
        if (result == NULL)
        {
            goto done;
        }
    }

done:
    Py_XDECREF(raised_list);
    Py_XDECREF(reraised_list);
    return result;
}

/* This function is used by the interpreter to construct reraised
 * exception groups. It takes an exception group eg and a list
 * of exception groups keep and returns the sub-exception group
 * of eg which contains all leaf exceptions that are contained
 * in any exception group in keep.
 */
static PyObject *
exception_group_projection(PyObject *eg, PyObject *keep)
{
    assert(_PyBaseExceptionGroup_Check(eg));
    assert(PyList_CheckExact(keep));

    PyObject *leaf_ids = PySet_New(NULL);
    if (!leaf_ids)
    {
        return NULL;
    }

    Py_ssize_t n = PyList_GET_SIZE(keep);
    for (Py_ssize_t i = 0; i < n; i++)
    {
        PyObject *e = PyList_GET_ITEM(keep, i);
        assert(e != NULL);
        assert(_PyBaseExceptionGroup_Check(e));
        if (collect_exception_group_leaf_ids(e, leaf_ids) < 0)
        {
            Py_DECREF(leaf_ids);
            return NULL;
        }
    }

    _exceptiongroup_split_result split_result;
    bool construct_rest = false;
    int err = exceptiongroup_split_recursive(
        eg, EXCEPTION_GROUP_MATCH_INSTANCE_IDS, leaf_ids,
        construct_rest, &split_result);
    Py_DECREF(leaf_ids);
    if (err < 0)
    {
        return NULL;
    }

    PyObject *result = split_result.match ? split_result.match : Py_NewRef(Py_None);
    assert(split_result.rest == NULL);
    return result;
}

static bool
is_same_exception_metadata(PyObject *exc1, PyObject *exc2)
{
    assert(PyExceptionInstance_Check(exc1));
    assert(PyExceptionInstance_Check(exc2));

    PyBaseExceptionObject *e1 = (PyBaseExceptionObject *)exc1;
    PyBaseExceptionObject *e2 = (PyBaseExceptionObject *)exc2;

    return (e1->notes == e2->notes &&
            e1->traceback == e2->traceback &&
            e1->cause == e2->cause &&
            e1->context == e2->context);
}

static int
collect_exception_group_leaf_ids(PyObject *exc, PyObject *leaf_ids)
{
    if (Py_IsNone(exc))
    {
        return 0;
    }

    assert(PyExceptionInstance_Check(exc));
    assert(PySet_Check(leaf_ids));

    /* Add IDs of all leaf exceptions in exc to the leaf_ids set */

    if (!_PyBaseExceptionGroup_Check(exc))
    {
        PyObject *exc_id = PyLong_FromVoidPtr(exc);
        if (exc_id == NULL)
        {
            return -1;
        }
        int res = PySet_Add(leaf_ids, exc_id);
        Py_DECREF(exc_id);
        return res;
    }
    PyBaseExceptionGroupObject *eg = _PyBaseExceptionGroupObject_cast(exc);
    Py_ssize_t num_excs = PyTuple_GET_SIZE(eg->excs);
    /* recursive calls */
    for (Py_ssize_t i = 0; i < num_excs; i++)
    {
        PyObject *e = PyTuple_GET_ITEM(eg->excs, i);
        if (_Py_EnterRecursiveCall(" in collect_exception_group_leaf_ids"))
        {
            return -1;
        }
        int res = collect_exception_group_leaf_ids(e, leaf_ids);
        _Py_LeaveRecursiveCall();
        if (res < 0)
        {
            return -1;
        }
    }
    return 0;
}

/*

2           0 SETUP_EXCEPT             3 (to 8)

  3           2 LOAD_GLOBAL              0 (TypeError)
              4 CALL_FUNCTION            0
              6 RAISE_VARARGS            1

  4     >>    8 POP_TOP
             10 DUP_TOP
             12 BUILD_LIST               0
             14 ROT_TWO
             16 LOAD_GLOBAL              0 (TypeError)
             18 <37>
             20 DUP_TOP
             22 LOAD_CONST               0 (None)
             24 IS_OP                    0
             26 POP_JUMP_IF_TRUE        23 (to 46)
             28 POP_TOP
             30 SETUP_EXCEPT             4 (to 40)

  5          32 LOAD_CONST               1 (1)
             34 STORE_FAST               0 (a)
             36 POP_BLOCK
             38 JUMP_FORWARD             4 (to 48)
        >>   40 LIST_APPEND              3
             42 POP_TOP
             44 JUMP_FORWARD             1 (to 48)
        >>   46 POP_TOP

  6     >>   48 LOAD_GLOBAL              1 (ValueError)
             50 <37>
             52 DUP_TOP
             54 LOAD_CONST               0 (None)
             56 IS_OP                    0
             58 POP_JUMP_IF_TRUE        39 (to 78)
             60 POP_TOP
             62 SETUP_EXCEPT             4 (to 72)

  7          64 LOAD_CONST               2 (2)
             66 STORE_FAST               0 (a)
             68 POP_BLOCK
             70 JUMP_FORWARD             4 (to 80)
        >>   72 LIST_APPEND              3
             74 POP_TOP
             76 JUMP_FORWARD             1 (to 80)
        >>   78 POP_TOP
        >>   80 LIST_APPEND              1
             82 <88>
             84 DUP_TOP
             86 LOAD_CONST               0 (None)
             88 IS_OP                    0
             90 POP_JUMP_IF_FALSE       48 (to 96)
             92 POP_TOP
             94 JUMP_FORWARD             3 (to 102)

  6     >>   96 POP_TOP
             98 POP_TOP
            100 RERAISE                  0

  8     >>  102 LOAD_CONST               1 (1)
            104 STORE_FAST               1 (@py_assert2)
            106 LOAD_FAST                0 (a)
            108 LOAD_FAST                1 (@py_assert2)
            110 COMPARE_OP               2 (==)
            112 STORE_FAST               2 (@py_assert1)
            114 LOAD_FAST                2 (@py_assert1)
            116 POP_JUMP_IF_TRUE       107 (to 214)
            118 LOAD_GLOBAL              2 (@pytest)
            120 LOAD_METHOD              3 (ar_call_reprcompare)
            122 LOAD_CONST               3 ((u'==',))
            124 LOAD_FAST                2 (@py_assert1)
            126 BUILD_TUPLE              1
            128 LOAD_CONST               4 ((u'%(py0)s == %(py3)s',))
            130 LOAD_FAST                0 (a)
            132 LOAD_FAST                1 (@py_assert2)
            134 BUILD_TUPLE              2
            136 CALL_METHOD              4
            138 LOAD_CONST               5 (u'a')
            140 LOAD_GLOBAL              4 (@py_builtins)
            142 LOAD_METHOD              5 (locals)
            144 CALL_METHOD              0
            146 CONTAINS_OP              0
            148 POP_JUMP_IF_TRUE        80 (to 160)
            150 LOAD_GLOBAL              2 (@pytest)
            152 LOAD_METHOD              6 (ar_should_repr_global_name)
            154 LOAD_FAST                0 (a)
            156 CALL_METHOD              1
            158 POP_JUMP_IF_FALSE       85 (to 170)
        >>  160 LOAD_GLOBAL              2 (@pytest)
            162 LOAD_METHOD              7 (ar_saferepr)
            164 LOAD_FAST                0 (a)
            166 CALL_METHOD              1
            168 JUMP_FORWARD             1 (to 172)
        >>  170 LOAD_CONST               5 (u'a')
        >>  172 LOAD_GLOBAL              2 (@pytest)
            174 LOAD_METHOD              7 (ar_saferepr)
            176 LOAD_FAST                1 (@py_assert2)
            178 CALL_METHOD              1
            180 LOAD_CONST               6 ((u'py0', u'py3'))
            182 BUILD_CONST_KEY_MAP      2
            184 BINARY_MODULO
            186 STORE_FAST               3 (@py_format4)
            188 LOAD_CONST               7 (u'assert %(py5)s')
            190 LOAD_FAST                3 (@py_format4)
            192 LOAD_CONST               8 ((u'py5',))
            194 BUILD_CONST_KEY_MAP      1
            196 BINARY_MODULO
            198 STORE_FAST               4 (@py_format6)
            200 LOAD_GLOBAL              8 (AssertionError)
            202 LOAD_GLOBAL              2 (@pytest)
            204 LOAD_METHOD              9 (ar_format_explanation)
            206 LOAD_FAST                4 (@py_format6)
            208 CALL_METHOD              1
            210 CALL_FUNCTION            1
            212 RAISE_VARARGS            1
        >>  214 LOAD_CONST               0 (None)
            216 DUP_TOP
            218 STORE_FAST               2 (@py_assert1)
            220 STORE_FAST               1 (@py_assert2)
            222 LOAD_CONST               0 (None)
            224 RETURN_VALUE

*/
