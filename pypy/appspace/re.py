# From CPython
def escape(pattern):
    "Escape all non-alphanumeric characters in pattern."
    s = list(pattern)
    for i in range(len(pattern)):
        c = pattern[i]
        if not ("a" <= c <= "z" or "A" <= c <= "Z" or "0" <= c <= "9"):
            if c == "\000":
                s[i] = "\\000"
            else:
                s[i] = "\\" + c
    return ''.join(s)

class Pattern:
    def __init__(self, pattern, flags):
        print 'regex', pattern
        print 'killed'
        raise SystemExit

_cache = {}

def compile(pattern, flags=0):
    if (pattern, flags) in _cache:
        return _cache[pattern, flags]
    compiled = Pattern(pattern, flags)
    _cache[pattern, flags] = compiled
    return compiled

def match(pattern, string, flags=0):
    return compile(pattern, flags).match(string)
