"""The application layer implementation of the _sre module."""

import sys
import _sre # Here we are importing the pypy version of _sre, (which is being
            # defined within this very file!). This is done in order to access
            # some methods written at interpreter level (they all start with
            # underscores).

__name__ = '_sre'
__doc__ = '_sre module: the core of the regular expression engine, implemented in C.'

def getcodesize():
    return _sre.CODESIZE


def compile(pattern, flags, code, groups=0, groupindex={}, indexgroup=[None]):
    import _sre
    result = _sre._compile(pattern, flags, code, groups, groupindex, indexgroup)
    return SRE_Pattern(result)
    

def _read_only_attribute(attr_name):
    """This is used to construct read-only attributes."""
    def fget(self):
        return _sre._fget(self._wrapped, attr_name)
    return property(fget)


class SRE_Pattern(object):
    def __init__(self, _wrapped):
        self._wrapped = _wrapped

    pattern = _read_only_attribute('pattern')
    flags = _read_only_attribute('flags')
    groups = _read_only_attribute('groups')
    groupindex = _read_only_attribute('groupindex')
    
    def match(self, pattern, pos=0, endpos=sys.maxint):
        """Searches through the string 'pattern' (which is the string
        to be searched, NOT the regular expression pattern) starting at
        pos and ending at endpos looking for matches to the pattern. If
        any are found it returns a SRE_Match match object; if no matches
        are found it returns None."""
        result = _sre._SRE_Pattern_match(self._wrapped, pattern, pos, endpos)
        if result is None:
            return None
        else:
            return SRE_Match(result, self)
            
    def search(self, pattern, pos=0, endpos=sys.maxint):
        result = _sre._SRE_Pattern_search(self._wrapped, pattern, pos, endpos)
        if result is None:
            return None
        else:
            return SRE_Match(result, self)
            
    def findall(self, string):
        return _sre._SRE_Pattern_findall(self._wrapped, string)
        
    def sub(self, repl, string, count=0):
        return _sre._SRE_Pattern_sub(self._wrapped, repl, string, count)
    
    def subn(self, repl, string, count=0):
        return _sre._SRE_Pattern_subn(self._wrapped, repl, string, count)
        
    def split(self, string, maxsplit=0):
        return _sre._SRE_Pattern_split(self._wrapped, string, maxsplit)

    def finditer(self, string):
        result = _sre._SRE_Pattern_finditer(self._wrapped, string)
        return SRE_Finditer(result, self)
        
    def scanner(self, string, start=0, end=sys.maxint):
        result = _sre._SRE_Pattern_scanner(self._wrapped, string, start, end)
        return SRE_Scanner(result, self)
    
    def __copy__():
        raise TypeError, 'cannot copy this pattern object'

    def __deepcopy__():
        raise TypeError, 'cannot copy this pattern object'
        


class SRE_Finditer(object):
    def __init__(self, _wrapped, _re):
        self._wrapped = _wrapped
        self._re = _re
    def __iter__(self):
        return self
    def next(self):
        match_obj = _sre._SRE_Finditer_next(self._wrapped)
        return SRE_Match( match_obj, self._re)
        
        
class SRE_Scanner(object):
    def __init__(self, _wrapped, pattern):
        self._wrapped = _wrapped
        self.pattern = pattern
    
    def match(self):
        """Returns a match object if the string matches the pattern
        starting at the current position, and advances the current position to
        the end of the match. Returns None if the string fails to match the
        pattern at the current position."""
        match_obj = _sre._SRE_Scanner_match(self._wrapped)
        if match_obj is None:
            return None
        else:
            return SRE_Match( match_obj, self.pattern )

    def search(self):
        """Returns a match object if the string matches the pattern anywhere
        on or after the current position, and advances the curent position to
        the end of the match. Returns None if the string fails to match the
        pattern at the current position."""
        match_obj = _sre._SRE_Scanner_search(self._wrapped)
        if match_obj is None:
            return None
        else:
            return SRE_Match( match_obj, self.pattern )


class SRE_Match(object):
    def __init__(self, _wrapped, re):
        self._wrapped = _wrapped
        self.re = re

    string = _read_only_attribute('string')
    pos = _read_only_attribute('pos')
    endpos = _read_only_attribute('endpos')
    lastindex = _read_only_attribute('lastindex')
    lastgroup = _read_only_attribute('lastgroup')
    regs = _read_only_attribute('regs')
        
    def start(self, group=0):
        return _sre._SRE_Match_start(self._wrapped, group)

    def end(self, group=0):
        return _sre._SRE_Match_end(self._wrapped, group)

    def span(self, group=0):
        return _sre._SRE_Match_span(self._wrapped, group)
        
    def expand(self, template):
        return _sre._SRE_Match_expand(self._wrapped, template)
        
    def groups(self, default=None):
        return _sre._SRE_Match_groups(self._wrapped, default)
        
    def groupdict(self, default=None):
        return _sre._SRE_Match_groupdict(self._wrapped, default)
        
    def group(self, *args):
        return _sre._SRE_Match_group(self._wrapped, args)
        
    def __copy__():
        raise TypeError, 'cannot copy this pattern object'

    def __deepcopy__():
        raise TypeError, 'cannot copy this pattern object'

