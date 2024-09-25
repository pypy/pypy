# code adapted from https://github.com/agronholm/exceptiongroup/, under MIT License

from collections.abc import Sequence

class BaseExceptionGroup(BaseException):
    """A combination of unrelated exceptions."""

    def __new__(cls, message, exceptions):
        if not isinstance(message, str):
            raise TypeError(f"argument 1 must be str, not {type(message)}")
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

        instance = super().__new__(cls, message, exceptions)
        instance._message = message
        instance._exceptions = tuple(exceptions)
        return instance

    @property
    def message(self):
        return self._message

    @property
    def exceptions(self):
        return self._exceptions

    def subgroup(self, condition):
        """
        Returns an exception group that contains only the exceptions from the
        current group that match condition, or None if the result is empty.
        """

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
        """
        Like subgroup(), but returns the pair (match, rest) where match is
        subgroup(condition) and rest is the remaining non-matching part.
        """
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

    def derive(self, excs):
        """
        Returns an exception group with the same message, but which wraps the
        exceptions in excs.
        """
        return BaseExceptionGroup(self.message, excs)

    def __str__(self):
        suffix = "" if len(self._exceptions) == 1 else "s"
        return f"{self.message} ({len(self._exceptions)} sub-exception{suffix})"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.message!r}, {list(self._exceptions)!r})"

class ExceptionGroup(BaseExceptionGroup, Exception):
    pass


def _derive_and_copy_attrs(self, excs):
    eg = self.derive(excs)
    if hasattr(self, "__notes__"):
        # Create a new list so that add_note() only affects one exceptiongroup
        eg.__notes__ = list(self.__notes__)
    eg.__cause__ = self.__cause__
    eg.__context__ = self.__context__
    eg.__traceback__ = self.__traceback__
    return eg

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
    # TODO: muss es nicht eigentlich anders herum sein
    # (return rest instead of match)?
    assert isinstance(eg, BaseExceptionGroup)
    assert isinstance(keep_list, list)

    resultset = set()
    for keep in keep_list:
        _collect_eg_leafs(keep, resultset)

    # TODO: maybe don't construct rest eg
    split_match, _ = eg.split(lambda element: element in resultset)

    return split_match

def _collect_eg_leafs(eg_or_exc, resultset):
    if eg_or_exc == None:
        # empty exception groups appear as a result
        # of matches (split, subgroup) and thus are valid
        pass
    elif isinstance(eg_or_exc, BaseExceptionGroup):
        # recursively collect children of eg
        for subexc in eg_or_exc._exceptions:
            _collect_eg_leafs(subexc, resultset)
    elif isinstance(eg_or_exc, BaseException):
        # we have a single exception (not a group),
        # return a singleton list containing the exc
        resultset.add(eg_or_exc)
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
        if exc != None:
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


_SENTINEL = object()

def _is_same_exception_metadata(exc1, exc2):
    # TODO: Exception or BaseException?
    assert isinstance(exc1, Exception)
    assert isinstance(exc2, Exception)

    return (getattr(exc1, '__notes__', _SENTINEL) == getattr(exc2, '__notes__', _SENTINEL) and
            exc1.__traceback__ == exc2.__traceback__ and
            exc1.__cause__     == exc2.__cause__ and
            exc1.__context__   == exc2.__context__)

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

