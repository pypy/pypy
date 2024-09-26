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
        eg.__notes__ = list(self.__notes__)
    eg.__cause__ = self.__cause__
    eg.__context__ = self.__context__
    eg.__traceback__ = self.__traceback__
    return eg


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

