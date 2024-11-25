# helper functions for interp_group.py that are exposed via a gateway.applevel


def check_new_args(cls, message, exceptions):
    if not isinstance(message, str):
        raise TypeError(f"argument 1 must be str, not {type(message)}")
    if not isinstance(exceptions, (list, tuple)):
        from collections.abc import Sequence
        if not isinstance(exceptions, Sequence):
            raise TypeError("second argument (exceptions) must be a sequence")
    if not exceptions or not exceptions.count:
        raise ValueError("second argument (exceptions) must be a non-empty sequence")

    for i, exc in enumerate(exceptions):
        if not isinstance(exc, BaseException):
            raise ValueError(f"Item {i} of second argument (exceptions) is not an exception")

    if cls is BaseExceptionGroup:
        if all(isinstance(exc, Exception) for exc in exceptions):
            cls = ExceptionGroup

    if issubclass(cls, Exception):
        for exc in exceptions:
            if not isinstance(exc, Exception):
                if cls is ExceptionGroup:
                    raise TypeError("Cannot nest BaseExceptions in an ExceptionGroup")
                else:
                    raise TypeError(f"Cannot nest BaseExceptions in {cls.__name__!r}")
    return cls, tuple(exceptions)

def subgroup(self, condition):
    condition = get_condition_filter(condition)
    modified = False
    if condition(self):
        return self

    exceptions = []
    for exc in self.exceptions:
        if isinstance(exc, BaseExceptionGroup):
            subgroup = exc.subgroup(condition)
            if subgroup is not None:
                exceptions.append(subgroup)
            if subgroup is not exc:
                modified = True
        elif condition(exc):
            exceptions.append(exc)
        else:
            modified = True

    if not modified:
        # this is the difference to split!
        return self
    elif exceptions:
        group = _derive_and_copy_attrs(self, exceptions)
        return group
    else:
        return None

def split(self, condition):
    condition = get_condition_filter(condition)
    if condition(self):
        return self, None

    matching_exceptions = []
    nonmatching_exceptions = []
    for exc in self.exceptions:
        if isinstance(exc, BaseExceptionGroup):
            matching, nonmatching = exc.split(condition)
            if matching is not None:
                matching_exceptions.append(matching)
            if nonmatching is not None:
                nonmatching_exceptions.append(nonmatching)
        elif condition(exc):
            matching_exceptions.append(exc)
        else:
            nonmatching_exceptions.append(exc)

    matching_group = None
    if matching_exceptions:
        matching_group = _derive_and_copy_attrs(self, matching_exceptions)

    nonmatching_group = None
    if nonmatching_exceptions:
        nonmatching_group = _derive_and_copy_attrs(self, nonmatching_exceptions)

    return (matching_group, nonmatching_group)

def __str__(self):
    suffix = "" if len(self.exceptions) == 1 else "s"
    return f"{self.message} ({len(self.exceptions)} sub-exception{suffix})"

def __repr__(self):
    return f"{self.__class__.__name__}({self.message!r}, {list(self.exceptions)!r})"

def _derive_and_copy_attrs(self, excs):
    eg = self.derive(excs)
    if hasattr(self, "__notes__"):
        # Create a new list so that add_note() only affects one exceptiongroup
        try:
            eg.__notes__ = list(self.__notes__)
        except TypeError:
            # ignore non-sequence __notes__
            pass
    eg.__cause__ = self.__cause__
    eg.__context__ = self.__context__
    eg.__traceback__ = self.__traceback__
    return eg


_SENTINEL = object()

def _is_same_exception_metadata(exc1, exc2):
    # TODO: Exception or BaseException?
    assert isinstance(exc1, Exception)
    assert isinstance(exc2, Exception)

    return (getattr(exc1, '__notes__', _SENTINEL) is getattr(exc2, '__notes__', _SENTINEL) and
            exc1.__traceback__ is exc2.__traceback__ and
            exc1.__cause__     is exc2.__cause__ and
            exc1.__context__   is exc2.__context__)

def get_condition_filter(condition):
    if isinstance(condition, type) and issubclass(condition, BaseException):
        return lambda exc: isinstance(exc, condition)
    elif isinstance(condition, tuple) and \
            all((isinstance(c, type) and issubclass(c, BaseException)) for c in condition):
        return lambda exc: isinstance(exc, condition)
    elif callable(condition):
        return condition
    # otherwise
    raise TypeError("expected a function, exception type or tuple of exception types")

# helper functions for the interpreter

def _exception_group_projection(eg, keep_list):
    """
    From CPython:
    /* This function is used by the interpreter to construct reraised
    * exception groups. It takes an exception group eg and a list
    * of exception groups keep and returns the sub-exception group
    * of eg which contains all leaf exceptions that are contained
    * in any exception group in keep.
    */
    """
    from __pypy__ import identity_dict
    # TODO: muss es nicht eigentlich anders herum sein
    # (return rest instead of match)?
    assert isinstance(eg, BaseExceptionGroup)
    assert isinstance(keep_list, list)

    resultset = identity_dict()
    for keep in keep_list:
        _collect_eg_leafs(keep, resultset)

    # TODO: maybe don't construct rest eg
    split_match, _ = eg.split(lambda element: element in resultset)

    return split_match

def _collect_eg_leafs(eg_or_exc, resultset):
    if eg_or_exc is None:
        # empty exception groups appear as a result
        # of matches (split, subgroup) and thus are valid
        pass
    elif isinstance(eg_or_exc, BaseExceptionGroup):
        # recursively collect children of eg
        for subexc in eg_or_exc.exceptions:
            _collect_eg_leafs(subexc, resultset)
    elif isinstance(eg_or_exc, BaseException):
        # we have a single exception (not a group),
        # return a singleton list containing the exc
        resultset[eg_or_exc] = None
    else:
        raise TypeError(f"expected BaseException, got {type(eg_or_exc)}")

def _prep_reraise_star(orig, exc_list):
    assert isinstance(orig, BaseException)
    assert isinstance(exc_list, list)

    # TODO: test this:
    if len(exc_list) < 1:
        return None

    for exc in exc_list: assert isinstance(exc, BaseException) or exc is None

    if not isinstance(orig, BaseExceptionGroup):
        # a naked exception was caught and wrapped. Only one except* clause
        # could have executed,so there is at most one exception to raise.
        assert len(exc_list) == 1 or (len(exc_list) == 2 and exc_list[1] is None)
        return exc_list[0]

    raised_list = []
    reraised_list = []
    for exc in exc_list:
        if exc is not None:
            if _is_same_exception_metadata(exc, orig):
                reraised_list.append(exc)
            else:
                raised_list.append(exc)

    reraised_eg = _exception_group_projection(orig, reraised_list)
    if reraised_eg is not None:
        assert _is_same_exception_metadata(reraised_eg, orig)

    if not raised_list:
        return reraised_eg
    if reraised_eg is not None:
        raised_list.append(reraised_eg)
    if len(raised_list) == 1:
        return raised_list[0]
    return ExceptionGroup("", raised_list)

