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
