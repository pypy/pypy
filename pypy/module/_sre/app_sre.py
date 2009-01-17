# NOT_RPYTHON
"""
A pure Python reimplementation of the _sre module from CPython 2.4
Copyright 2005 Nik Haldimann, licensed under the MIT license

This code is based on material licensed under CNRI's Python 1.6 license and
copyrighted by: Copyright (c) 1997-2001 by Secret Labs AB
"""

import sys
import _sre


def compile(pattern, flags, code, groups=0, groupindex={}, indexgroup=[None]):
    """Compiles (or rather just converts) a pattern descriptor to a SRE_Pattern
    object. Actual compilation to opcodes happens in sre_compile."""
    return SRE_Pattern(pattern, flags, code, groups, groupindex, indexgroup)


class SRE_Pattern(object):

    def __init__(self, pattern, flags, code, groups=0, groupindex={}, indexgroup=[None]):
        self.pattern = pattern
        self.flags = flags
        self.groups = groups
        self.groupindex = groupindex # Maps group names to group indices
        self._indexgroup = indexgroup # Maps indices to group names
        self._code = code
    
    def match(self, string, pos=0, endpos=sys.maxint):
        """If zero or more characters at the beginning of string match this
        regular expression, return a corresponding MatchObject instance. Return
        None if the string does not match the pattern."""
        state = _sre._State(string, pos, endpos, self.flags)
        if _sre._match(state, self._code):
            return SRE_Match(self, state)
        else:
            return None

    def search(self, string, pos=0, endpos=sys.maxint):
        """Scan through string looking for a location where this regular
        expression produces a match, and return a corresponding MatchObject
        instance. Return None if no position in the string matches the
        pattern."""
        state = _sre._State(string, pos, endpos, self.flags)
        if _sre._search(state, self._code):
            return SRE_Match(self, state)
        else:
            return None

    def findall(self, string, pos=0, endpos=sys.maxint):
        """Return a list of all non-overlapping matches of pattern in string."""
        matchlist = []
        state = _sre._State(string, pos, endpos, self.flags)
        while state.start <= state.end:
            state.reset()
            if not _sre._search(state, self._code):
                break
            match = SRE_Match(self, state)
            if self.groups == 0 or self.groups == 1:
                item = match.group(self.groups)
            else:
                item = match.groups("")
            matchlist.append(item)
            if state.string_position == state.start:
                state.start += 1
            else:
                state.start = state.string_position
        return matchlist        
        
    def subn(self, repl, string, count=0):
        """Return the tuple (new_string, number_of_subs_made) found by replacing
        the leftmost non-overlapping occurrences of pattern with the replacement
        repl."""
        filter = repl
        if not callable(repl) and "\\" in repl:
            # handle non-literal strings ; hand it over to the template compiler
            import re
            filter = re._subx(self, repl)
        state = _sre._State(string, 0, sys.maxint, self.flags)
        sublist = []

        need_unicode = (isinstance(string, unicode) or
                        isinstance(repl, unicode))
        n = last_pos = 0
        while not count or n < count:
            state.reset()
            if not _sre._search(state, self._code):
                break
            if last_pos < state.start:
                sublist.append(string[last_pos:state.start])
            if not (last_pos == state.start and
                                last_pos == state.string_position and n > 0):
                # the above ignores empty matches on latest position
                if callable(filter):
                    to_app = filter(SRE_Match(self, state))
                else:
                    to_app = filter
                if isinstance(to_app, unicode):
                    need_unicode = True
                sublist.append(to_app)
                last_pos = state.string_position
                n += 1
            if state.string_position == state.start:
                state.start += 1
            else:
                state.start = state.string_position

        if last_pos < state.end:
            sublist.append(string[last_pos:state.end])

        if n == 0:
            # not just an optimization -- see test_sub_unicode
            return string, n

        if need_unicode:
            item = u"".join(sublist)
        else:
            item = "".join(sublist)
        return item, n

    def sub(self, repl, string, count=0):
        """Return the string obtained by replacing the leftmost non-overlapping
        occurrences of pattern in string by the replacement repl."""
        item, n = self.subn(repl, string, count)
        return item
        
    def split(self, string, maxsplit=0):
        """Split string by the occurrences of pattern."""
        splitlist = []
        state = _sre._State(string, 0, sys.maxint, self.flags)
        n = 0
        last = state.start
        while not maxsplit or n < maxsplit:
            state.reset()
            if not _sre._search(state, self._code):
                break
            if state.start == state.string_position: # zero-width match
                if last == state.end:                # or end of string
                    break
                state.start += 1
                continue
            splitlist.append(string[last:state.start])
            # add groups (if any)
            if self.groups:
                match = SRE_Match(self, state)
                splitlist.extend(list(match.groups(None)))
            n += 1
            last = state.start = state.string_position
        splitlist.append(string[last:state.end])
        return splitlist

    def finditer(self, string, pos=0, endpos=sys.maxint):
        """Return a list of all non-overlapping matches of pattern in string."""
        scanner = self.scanner(string, pos, endpos)
        return iter(scanner.search, None)

    def scanner(self, string, start=0, end=sys.maxint):
        return SRE_Scanner(self, string, start, end)
    
    def __copy__(self):
        raise TypeError, "cannot copy this pattern object"

    def __deepcopy__(self):
        raise TypeError, "cannot copy this pattern object"


class SRE_Scanner(object):
    """Undocumented scanner interface of sre."""
    
    def __init__(self, pattern, string, start, end):
        self.pattern = pattern
        self._state = _sre._State(string, start, end, self.pattern.flags)

    def _match_search(self, matcher):
        state = self._state
        state.reset()
        match = None
        if matcher(state, self.pattern._code):
            match = SRE_Match(self.pattern, state)
        if match is None or state.string_position == state.start:
            state.start += 1
        else:
            state.start = state.string_position
        return match

    def match(self):
        return self._match_search(_sre._match)

    def search(self):
        return self._match_search(_sre._search)


class SRE_Match(object):

    def __init__(self, pattern, state):
        self.re = pattern
        self.string = state.string
        self.pos = state.pos
        self.endpos = state.end
        self.lastindex = state.lastindex
        if self.lastindex < 0:
            self.lastindex = None
        self.regs = state.create_regs(self.re.groups)
        if pattern._indexgroup and 0 <= self.lastindex < len(pattern._indexgroup):
            # The above upper-bound check should not be necessary, as the re
            # compiler is supposed to always provide an _indexgroup list long
            # enough. But the re.Scanner class seems to screw up something
            # there, test_scanner in test_re won't work without upper-bound
            # checking. XXX investigate this and report bug to CPython.
            self.lastgroup = pattern._indexgroup[self.lastindex]
        else:
            self.lastgroup = None

    def _get_index(self, group):
        if isinstance(group, int):
            if group >= 0 and group <= self.re.groups:
                return group
        else:
            if self.re.groupindex.has_key(group):
                return self.re.groupindex[group]
        raise IndexError("no such group")

    def _get_slice(self, group, default):
        group_indices = self.regs[group]
        if group_indices[0] >= 0:
            return self.string[group_indices[0]:group_indices[1]]
        else:
            return default

    def start(self, group=0):
        """Returns the indices of the start of the substring matched by group;
        group defaults to zero (meaning the whole matched substring). Returns -1
        if group exists but did not contribute to the match."""
        return self.regs[self._get_index(group)][0]

    def end(self, group=0):
        """Returns the indices of the end of the substring matched by group;
        group defaults to zero (meaning the whole matched substring). Returns -1
        if group exists but did not contribute to the match."""
        return self.regs[self._get_index(group)][1]

    def span(self, group=0):
        """Returns the 2-tuple (m.start(group), m.end(group))."""
        return self.start(group), self.end(group)
        
    def expand(self, template):
        """Return the string obtained by doing backslash substitution and
        resolving group references on template."""
        import re
        return re._expand(self.re, self, template)
        
    def groups(self, default=None):
        """Returns a tuple containing all the subgroups of the match. The
        default argument is used for groups that did not participate in the
        match (defaults to None)."""
        groups = []
        for indices in self.regs[1:]:
            if indices[0] >= 0:
                groups.append(self.string[indices[0]:indices[1]])
            else:
                groups.append(default)
        return tuple(groups)
        
    def groupdict(self, default=None):
        """Return a dictionary containing all the named subgroups of the match.
        The default argument is used for groups that did not participate in the
        match (defaults to None)."""
        groupdict = {}
        for key, value in self.re.groupindex.items():
            groupdict[key] = self._get_slice(value, default)
        return groupdict

    def group(self, *args):
        """Returns one or more subgroups of the match. Each argument is either a
        group index or a group name."""
        if len(args) == 0:
            args = (0,)
        grouplist = []
        for group in args:
            grouplist.append(self._get_slice(self._get_index(group), None))
        if len(grouplist) == 1:
            return grouplist[0]
        else:
            return tuple(grouplist)

    def __copy__():
        raise TypeError, "cannot copy this pattern object"

    def __deepcopy__():
        raise TypeError, "cannot copy this pattern object"
