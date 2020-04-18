""" Test the re module by constructing random syntax trees of (a subset of)
regular expressions. A tree can be used to generate matching or optionally
non-matching strings. A tree can also be turned into re syntax."""

import re
import sys
import time
from contextlib import contextmanager
from functools import partial

from hypothesis import given, strategies as st, note, reproduce_failure

from rpython.rlib.rsre.test.test_match import get_code
from rpython.rlib.rsre import rsre_utf8, rsre_constants as consts, rsre_char
from rpython.rlib.unicodedata import unicodedb
rsre_char.set_unicode_db(unicodedb)


special_characters = ".^$*+?{}\\[]-|()#=!"
MAXREPEAT = 7


class State:
    def __init__(self):
        self.groups = {}


class CantGenerateNonMatching(Exception):
    pass


class Re:
    """ abstract base class for regular expression syntax nodes """

    def can_be_empty(self):
        """ Can self match the empty string? """
        return False

    def matching_string(self, draw, state):
        """ use draw to generate a string that is known to match self """
        raise NotImplementedError

    def non_matching_string(self, draw, state):
        """ try to use draw to generate a string that *doesn't* match self. Can
        fail by raising CantGenerateNonMatching """
        raise NotImplementedError

    def build_re(self):
        """ Build the re syntax for self """
        raise NotImplementedError


class Char(Re):
    """ Matches a single character self.c"""

    def __init__(self, c):
        self.c = c

    def matching_string(self, draw, state):
        return self.c

    def non_matching_string(self, draw, state):
        return draw(st.characters(blacklist_characters=self.c))

    def build_re(self):
        return self.c

    @staticmethod
    def make(draw):
        exp = draw(st.characters(blacklist_characters=special_characters))
        return Char(exp)


class CharClass(Re):
    """ Matches a (unicode) character category, positively or negatively """

    def __init__(self, char, unicat, polarity_cat):
        self.char = char
        self.unicat = unicat
        self.polarity_cat = polarity_cat

    def matching_string(self, draw, state):
        if self.polarity_cat:
            return draw(st.characters(whitelist_categories=self.unicat))
        return draw(st.characters(blacklist_categories=self.unicat))

    def non_matching_string(self, draw, state):
        if self.polarity_cat:
            return draw(st.characters(blacklist_categories=self.unicat))
        return draw(st.characters(whitelist_categories=self.unicat))

    def build_re(self):
        return u"\\" + self.char

    @staticmethod
    def make(draw):
        # XXX can add more
        return CharClass(
            *draw(st.sampled_from([("d", ["Nd"], True), ("D", ["Nd"], False)]))
        )


class Dot(Re):
    """ The regular expression '.', matches anything except a newline. """

    def matching_string(self, draw, state):
        return draw(st.characters(blacklist_characters="\n"))

    def non_matching_string(self, draw, state):
        return u"\n"

    def build_re(self):
        return u"."

    @staticmethod
    def make(draw):
        return Dot()


class Escape(Re):
    """ A regular expression escape. """

    def __init__(self, c):
        self.c = c

    def matching_string(self, draw, state):
        return self.c

    def non_matching_string(self, draw, state):
        return draw(st.characters(blacklist_characters=self.c))

    def build_re(self):
        return u"\\" + self.c

    @staticmethod
    def make(draw):
        # XXX many more escapes
        c = draw(st.sampled_from(special_characters))
        return Escape(c)


class Charset(Re):
    """ A character set [...]. The elements are either single characters or
    ranges represented by (start, stop) tuples. """

    def __init__(self, elements):
        # XXX character classes
        self.elements = elements

    def matching_string(self, draw, state):
        x = draw(st.sampled_from(self.elements))
        if isinstance(x, tuple):
            return draw(st.characters(min_codepoint=ord(x[0]), max_codepoint=ord(x[1])))
        return x

    def non_matching_string(self, draw, state):
        if not any(isinstance(x, tuple) for x in self.elements):
            # easy case, only chars
            return draw(st.characters(blacklist_characters=self.elements))
        chars = u"".join(x for x in self.elements if not isinstance(x, tuple))
        range_stops = [ord(x[1]) for x in self.elements if isinstance(x, tuple)]
        max_stop = max(range_stops)
        res = draw(
            st.characters(min_codepoint=max_stop + 1, blacklist_characters=chars)
        )
        return res

    def build_re(self):
        res = []
        for x in self.elements:
            if isinstance(x, tuple):
                res.append(u"%s-%s" % x)
            else:
                res.append(x)
        return u"[" + u"".join(res) + u"]"

    @staticmethod
    def make(draw):
        elements = draw(st.lists(Charset.charset_elements(), min_size=2, max_size=20))
        return Charset(elements)

    @staticmethod
    @st.composite
    def charset_elements(draw):
        """ Generate an element of a character set element, either a single
        character or a character range, represented by a tuple. """
        if draw(st.booleans()):
            # character
            return draw(st.characters(blacklist_characters="-^]\\"))
        else:
            start = draw(st.characters(blacklist_characters="-^]\\"))
            stop = draw(
                st.characters(
                    blacklist_characters="-^]\\", min_codepoint=ord(start) + 1
                )
            )
            return start, stop


class CharsetComplement(Re):
    """ An complemented character set [^...]"""

    def __init__(self, charset):
        assert isinstance(charset, Charset)
        self.charset = charset

    def matching_string(self, draw, state):
        return self.charset.non_matching_string(draw, state)

    def non_matching_string(self, draw, state):
        return self.charset.matching_string(draw, state)

    def build_re(self):
        charset = self.charset.build_re()
        assert charset.startswith(u"[")
        return u"[^%s]" % charset[1:-1]

    @staticmethod
    def make(draw):
        return CharsetComplement(Charset.make(draw))


def re_simple(draw):
    """ Generate a "simple" regular expression, either '.', a single character,
    an escaped character a character category, a charset or its complement. """
    cls = draw(
        st.sampled_from([Dot, Char, Escape, CharClass, Charset, CharsetComplement])
    )
    return cls.make(draw)


class RecursiveRe(Re):
    """ Abstract base class for "recursive" Re nodes, ie nodes that build on
    top of other nodes. """

    @staticmethod
    def make_with_base(base, draw):
        """ Factory function to construct a random instance of the current
        class. The nodes that this class builds upons are constructed using
        base, which has to be a function that takes draw, and returns an
        instance of (a subclass of) Re."""
        raise NotImplementedError


class Repetition(RecursiveRe):
    """ Abstract base class for "repetition"-like Re nodes. Can be either
    minimally matching (lazy) or maximally (greedy). """

    # minimum number of repetitions of self.base
    # subclasses need to define that attribute, either on the class or instance
    istart = None
    # maximum number of repetitions of self.base
    # subclasses need to define that attribute, either on the class or instance
    istop = None

    def __init__(self, base, lazy):
        self.base = base
        self.lazy = lazy

    def can_be_empty(self):
        return self.base.can_be_empty() or self.istart == 0

    def build_re(self):
        return self._build_re() + u"?" * self.lazy

    def _build_re(self):
        raise NotImplementedError

    def matching_string(self, draw, state):
        repetition = draw(st.integers(min_value=self.istart, max_value=self.istop))
        res = [self.base.matching_string(draw, state) for i in range(repetition)]
        return u"".join(res)

    def non_matching_string(self, draw, state):
        if self.can_be_empty() or self.base.can_be_empty():
            raise CantGenerateNonMatching
        res = [self.base.matching_string(draw, state) for i in range(self.istart)]
        non_matching_pos = draw(st.integers(min_value=0, max_value=len(res) - 1))
        res[non_matching_pos] = self.base.non_matching_string(draw, state)
        return u"".join(res)

    @staticmethod
    def make_with_base(base, draw):
        b = base(draw)
        cls = draw(
            st.sampled_from(
                [Questionmark, Star, Plus, FixedNum, Start, Stop, StartStop]
            )
        )
        return cls.make_repetition(b, draw)


class Questionmark(Repetition):
    istart = 0
    istop = 1

    def _build_re(self):
        return self.base.build_re() + u"?"

    @staticmethod
    def make_repetition(base, draw):
        return Questionmark(base, draw(st.booleans()))


class Star(Repetition):
    """ A Kleene-Star * regular expression, repeating the base expression 0 or
    more times. """

    istart = 0
    istop = MAXREPEAT

    def _build_re(self):
        return self.base.build_re() + u"*"

    @staticmethod
    def make_repetition(base, draw):
        return Star(base, draw(st.booleans()))


class Plus(Repetition):
    """ A + regular expression repeating the base expression 1 or more
    times."""

    istart = 1
    istop = MAXREPEAT

    def _build_re(self):
        return self.base.build_re() + u"+"

    @staticmethod
    def make_repetition(base, draw):
        return Plus(base, draw(st.booleans()))


class FixedNum(Repetition):
    """ Repeating the base expression a fixed number of times. """

    def __init__(self, base, num, lazy):
        Repetition.__init__(self, base, lazy)
        self.istart = self.istop = num

    def _build_re(self):
        return u"%s{%s}" % (self.base.build_re(), self.istart)

    @staticmethod
    def make_repetition(base, draw):
        num = draw(st.integers(min_value=0, max_value=MAXREPEAT))
        return FixedNum(base, num, draw(st.booleans()))


class StartStop(Repetition):
    """ Repeating the base expression between istart and istop many times. """

    def __init__(self, base, istart, istop, lazy):
        Repetition.__init__(self, base, lazy)
        self.istart = istart
        self.istop = istop

    def _build_re(self):
        return u"%s{%s,%s}" % (self.base.build_re(), self.istart, self.istop)

    @staticmethod
    def make_repetition(base, draw):
        start = draw(st.integers(min_value=0, max_value=MAXREPEAT))
        stop = draw(st.integers(min_value=start, max_value=MAXREPEAT))
        return StartStop(base, start, stop, draw(st.booleans()))


class Stop(Repetition):
    """ Repeating the base expression between 0 and istop many times. """

    istart = 0

    def __init__(self, base, istop, lazy):
        Repetition.__init__(self, base, lazy)
        self.istop = istop

    def _build_re(self):
        return u"%s{,%s}" % (self.base.build_re(), self.istop)

    @staticmethod
    def make_repetition(base, draw):
        stop = draw(st.integers(min_value=0, max_value=MAXREPEAT))
        return Stop(base, stop, draw(st.booleans()))


class Start(Repetition):
    """ Repeating the base expression at least istart many times. """

    istop = MAXREPEAT

    def __init__(self, base, istart, lazy):
        Repetition.__init__(self, base, lazy)
        self.istart = istart

    def _build_re(self):
        return u"%s{%s,}" % (self.base.build_re(), self.istart)

    @staticmethod
    def make_repetition(base, draw):
        start = draw(st.integers(min_value=0, max_value=MAXREPEAT))
        return Start(base, start, draw(st.booleans()))


class Sequence(RecursiveRe):
    """ A sequence of other regular expressions, which need to match one after
    the other. """

    def __init__(self, bases):
        self.bases = bases

    def can_be_empty(self):
        return all(base.can_be_empty() for base in self.bases)

    def matching_string(self, draw, state):
        return u"".join(b.matching_string(draw, state) for b in self.bases)

    def non_matching_string(self, draw, state):
        if self.can_be_empty():
            raise CantGenerateNonMatching
        nonempty_positions = [
            i for (i, b) in enumerate(self.bases) if not b.can_be_empty()
        ]
        res = []
        for base_pos in nonempty_positions:
            res.append(self.bases[base_pos].non_matching_string(draw, state))
        return u"".join(res)

    def build_re(self):
        return u"".join(b.build_re() for b in self.bases)

    @staticmethod
    def make_with_base(base, draw):
        return Sequence(
            [
                base(draw)
                for i in range(draw(st.integers(min_value=2, max_value=MAXREPEAT)))
            ]
        )


class SequenceWithBackref(Sequence):
    """ Not really its own class, just a way to construct a sequence. Generate
    a random sequence and then turn one of the expressions into a named group,
    and add a reference to that group to the end of the sequence. """

    @staticmethod
    def make_with_base(base, draw):
        sequence = Sequence.make_with_base(base, draw)
        bases = sequence.bases
        # the following code would have found the bug in
        # https://foss.heptapod.net/pypy/pypy/commit/c83c263f9f00d18d48ef536947c9b61ca53e01a2
        group = draw(st.integers(min_value=0, max_value=len(bases) - 1))
        # generate then caches a set across the run
        used_names = draw(st.shared(st.builds(set), key="group names"))
        # XXX a lot more characters are safe identifiers
        name = draw(st.from_regex("\A[a-zA-Z_][a-zA-Z0-9_]*\Z").filter(lambda s: s not in used_names))
        used_names.add(name)
        bases[group] = g = NamedGroup(bases[group], name)
        bases.append(GroupReference(g))
        return sequence


class NamedGroup(RecursiveRe):
    """ Wrap the base expression into a named group with name. """

    def __init__(self, base, name):
        self.base = base
        self.name = name

    def can_be_empty(self):
        return self.base.can_be_empty()

    def build_re(self):
        return u"(?P<%s>%s)" % (self.name, self.base.build_re())

    def matching_string(self, draw, state):
        res = self.base.matching_string(draw, state)
        state.groups[self] = res
        return res

    def non_matching_string(self, draw, state):
        res = self.base.non_matching_string(draw, state)
        state.groups[self] = res
        return res

class NonCapturingGroup(RecursiveRe):
    """ Wrap the base expression into a non-capturing group. """

    def __init__(self, base):
        self.base = base

    def can_be_empty(self):
        return self.base.can_be_empty()

    def build_re(self):
        return u"(?:%s)" % (self.base.build_re(), )

    def matching_string(self, draw, state):
        return self.base.matching_string(draw, state)

    def non_matching_string(self, draw, state):
        return self.base.non_matching_string(draw, state)


class GroupReference(Re):
    """ Backreference to a named group. """

    def __init__(self, group):
        assert isinstance(group, NamedGroup)
        self.group = group

    def can_be_empty(self):
        return self.group.can_be_empty()

    def build_re(self):
        return u"(?P=%s)" % (self.group.name, )

    def matching_string(self, draw, state):
        return state.groups[self.group]

    def non_matching_string(self, draw, state):
        return state.groups[self.group]  # doesn't matter, the group can't match


class Disjunction(RecursiveRe):
    """ A disjunction of regular expressions, ie combining them with '|', where
    either of the base expressions has to match for the whole expression to
    match."""

    def __init__(self, bases):
        self.bases = bases

    def can_be_empty(self):
        return any(base.can_be_empty() for base in self.bases)

    def matching_string(self, draw, state):
        base = draw(st.sampled_from(self.bases))
        return base.matching_string(draw, state)

    def non_matching_string(self, draw, state):
        # XXX could be improved
        raise CantGenerateNonMatching

    def build_re(self):
        return u"|".join(b.build_re() for b in self.bases)

    @staticmethod
    def make_with_base(base, draw):
        return Disjunction(
            [
                base(draw)
                for i in range(draw(st.integers(min_value=2, max_value=MAXREPEAT)))
            ]
        )


# run some tests


@contextmanager
def assert_quick_not_quadratic():
    # Tests for timing can be brittle, but we think it's still worth checking
    # for pathologically slow (eg accidentally quadratic) performance issues.
    start = time.time()
    yield
    end = time.time()
    assert end - start < 1


def re_test(maker):
    """ Generate a test for the Re generating function maker. """

    @given(data=st.data())
    def test(data):
        draw = data.draw
        re_object = maker(draw)
        re_pattern = re_object.build_re()
        note(repr(re_pattern))
        compiled = get_code(re_pattern, consts.SRE_FLAG_UNICODE)

        # Sanity-check match on empty string is as we expect
        assert re_object.can_be_empty() == (rsre_utf8.utf8match(compiled, "") is not None)

        # Check that a string expected to match does in fact match
        syes = re_object.matching_string(draw, State())
        note(("yes", repr(syes)))
        with assert_quick_not_quadratic():
            assert rsre_utf8.utf8match(compiled, syes.encode("utf-8"))

        # Check that, if we can generate a string that is not expected to match,
        # that string really doesn't match.
        try:
            sno = re_object.non_matching_string(draw, State())
        except CantGenerateNonMatching:
            pass
        else:
            note(("no", repr(sno)))
            with assert_quick_not_quadratic():
                assert rsre_utf8.utf8match(compiled, sno.encode("utf-8")) is None

        # search test
        prefix = draw(st.text())
        together = prefix + syes
        note(("together", together))
        assert rsre_utf8.utf8search(compiled, together.encode("utf-8")).match_start <= len(prefix.encode("utf-8"))

    return test


# Simple test cases
test_char = re_test(Char.make)
test_dots = re_test(Dot.make)
test_escape = re_test(Escape.make)
test_charclass = re_test(CharClass.make)
test_charset = re_test(Charset.make)
test_simple = re_test(re_simple)

# Compound pattern types
simple_repetition = partial(Repetition.make_with_base, re_simple)
sequence_repetition = partial(Sequence.make_with_base, simple_repetition)
backref_sequence = partial(SequenceWithBackref.make_with_base, simple_repetition)
simple_disjunction = partial(Disjunction.make_with_base, re_simple)
disjunction_sequence = partial(Disjunction.make_with_base, backref_sequence)

# Tests for compound pattern types
test_simple_repetition = re_test(simple_repetition)
test_sequence_repetition = re_test(sequence_repetition)
test_backref_sequence = re_test(backref_sequence)
test_simple_disjunction = re_test(simple_disjunction)
test_disjunction_sequence_repetition = re_test(disjunction_sequence)


# Tests for searching

def make_prefix_re(draw):
    prefix = draw(st.lists(st.composite(Char.make)(), min_size=1, max_size=MAXREPEAT))
    rest = Disjunction.make_with_base(backref_sequence, draw)
    prefix.append(NonCapturingGroup(rest))
    return Sequence(prefix)

test_prefix_re = re_test(make_prefix_re)

