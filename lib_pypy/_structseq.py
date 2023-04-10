"""
Implementation helper: a struct that looks like a tuple.  See timemodule
and posixmodule for example uses.
"""
from __pypy__ import hidden_applevel

make_none = lambda self: None

class structseqfield(object):
    """Definition of field of a structseq.  The 'index' is for positional
    tuple-like indexing.  Fields whose index is after a gap in the numbers
    cannot be accessed like this, but only by name.
    """
    __name__ = "?"

    def __init__(self, index, doc=None, default=None):
        # these attributes should not be overwritten after setting them for the
        # first time, to make them immutable
        # self.__name__ is set later
        self.index    = index
        # self.is_positional = True/False, set later
        self.__doc__  = doc
        if default: # also written below
            self._default = default

    def __repr__(self):
        return '<field %s (%s)>' % (self.__name__,
                                    self.__doc__ or 'undocumented')

    @hidden_applevel
    def __get__(self, obj, typ=None):
        if obj is None:
            return self
        if not self.is_positional:
            return obj.__dict__[self.__name__]
        else:
            return obj[self.index]

    def __set__(self, obj, value):
        raise AttributeError("readonly attribute")


class structseqtype(type):

    def __new__(metacls, classname, bases, dict):
        assert not bases
        fields_by_index = {}
        for name, field in dict.items():
            if isinstance(field, structseqfield):
                assert field.index not in fields_by_index
                fields_by_index[field.index] = field
                field.__name__ = name
        dict['n_fields'] = len(fields_by_index)

        extra_fields = sorted(fields_by_index.items())
        n_sequence_fields = 0
        sequence_fields = []
        while extra_fields and extra_fields[0][0] == n_sequence_fields:
            num, field = extra_fields.pop(0)
            field.is_positional = True
            assert not hasattr(field, "_default")
            sequence_fields.append(field.__name__)
            n_sequence_fields += 1

        dict['n_sequence_fields'] = n_sequence_fields
        dict['n_unnamed_fields'] = 0     # no fully anonymous fields in PyPy

        extra_fields = [field for index, field in extra_fields]
        for field in extra_fields:
            field.is_positional = False
            if not hasattr(field, "_default"):
                field._default = make_none

        dict['_extra_fields'] = tuple(extra_fields)
        if '__new__' not in dict:
            dict['__new__'] = structseq_new
        dict['__reduce__'] = structseq_reduce
        dict['__setattr__'] = structseq_setattr
        dict['__repr__'] = structseq_repr
        dict['__str__'] = structseq_repr
        dict['_name'] = dict.get('name', classname)
        dict['__match_args__'] = tuple(sequence_fields)
        return type.__new__(metacls, classname, (tuple,), dict)


builtin_dict = dict

MISSING = object()

@hidden_applevel
def structseq_new(cls, sequence, dict=MISSING):
    if dict is MISSING:
        dict = {}
    elif not isinstance(dict, builtin_dict):
        raise TypeError(cls._name + " takes a dict as second arg, if any")
    N = cls.n_sequence_fields
    # total fields (unnamed are not yet supported, extra fields not included)
    if N == 1:
        sequence = tuple([sequence])
    else:
        sequence = tuple(sequence)
    if len(sequence) < N:
        if N < cls.n_fields:
            msg = "at least"
        else:
            msg = "exactly"
        raise TypeError("expected a sequence with %s %d items. has %d" % (
            msg, N, len(sequence)))
    if len(sequence) > N:
        if len(sequence) > cls.n_fields:
            if N < cls.n_fields:
                msg = "at most"
            else:
                msg = "exactly"
            raise TypeError("expected a sequence with %s %d items. has %d" \
                            % (msg, cls.n_fields, len(sequence)))
        result = tuple.__new__(cls, sequence[:N])
        difference = len(sequence) - N
        for i in range(len(sequence) - N):
            name = cls._extra_fields[i].__name__
            if name in dict:
                raise TypeError("duplicate value for %r" % (name,))
            result.__dict__[name] = sequence[N + i]
        startindex = len(sequence) - N
        if startindex == len(cls._extra_fields):
            return result
    else:
        result = tuple.__new__(cls, sequence)
        startindex = 0
    for i in range(startindex, len(cls._extra_fields)):
        field = cls._extra_fields[i]
        name = field.__name__
        try:
            value = dict[name]
        except KeyError:
            value = field._default(result)
        result.__dict__[name] = value
    return result

def structseq_reduce(self):
    return type(self), (tuple(self), self.__dict__)

def structseq_setattr(self, attr, value):
    if attr not in type(self).__dict__:
        raise AttributeError("%r object has no attribute %r" % (
            self.__class__.__name__, attr))
    else:
        raise AttributeError("readonly attribute")

def structseq_repr(self):
    fields = {}
    for field in type(self).__dict__.values():
        if isinstance(field, structseqfield):
            fields[field.index] = field
    parts = ["%s=%r" % (fields[index].__name__, value)
             for index, value in enumerate(self)]
    return "%s(%s)" % (self._name, ", ".join(parts))


class SimpleNamespace:
    """A simple attribute-based namespace.

SimpleNamespace(**kwargs)"""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        ident = id(self)
        if ident in sns_recurse:
            return "namespace(...)"
        sns_recurse.add(ident)
        try:
            pairs = ('%s=%r' % item for item in sorted(self.__dict__.items()))
            return "namespace(%s)" % ', '.join(pairs)
        finally:
            sns_recurse.discard(ident)

    def __eq__(self, other):
        if issubclass(type(other), SimpleNamespace):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __ne__(self, other):
        if issubclass(type(other), SimpleNamespace):
            return self.__dict__ != other.__dict__
        return NotImplemented

sns_recurse = set()

# This class is not exposed in sys, but by the types module.
SimpleNamespace.__module__ = 'types'
