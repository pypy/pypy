from pypy.rpython.lltypesystem import lltype
from pypy.translator.gensupp import NameManager

#
# use __slots__ declarations for node classes etc
# possible to turn it off while refactoring, experimenting
#
USESLOTS = True


class ErrorValue:
    def __init__(self, TYPE):
        self.TYPE = TYPE


#
# helpers
#
def cdecl(ctype, cname):
    """
    Produce a C declaration from a 'type template' and an identifier.
    The type template must contain a '@' sign at the place where the
    name should be inserted, according to the strange C syntax rules.
    """
    # the (@) case is for functions, where if there is a plain (@) around
    # the function name, we don't need the very confusing parenthesis
    return ctype.replace('(@)', '@').replace('@', cname).strip()

def somelettersfrom(s):
    upcase = [c for c in s if c.isupper()]
    if not upcase:
        upcase = [c for c in s.title() if c.isupper()]
    locase = [c for c in s if c.islower()]
    if locase and upcase:
        return ''.join(upcase).lower()
    else:
        return s[:2].lower()


def llvalue_from_constant(c):
    try:
        T = c.concretetype
    except AttributeError:
        return lltype.pyobjectptr(c.value)
    else:
        if T == lltype.Void:
            return None
        else:
            assert lltype.typeOf(c.value) == T
            return c.value


class CNameManager(NameManager):
    def __init__(self, global_prefix='pypy_'):
        NameManager.__init__(self, global_prefix=global_prefix)
        # keywords cannot be reused.  This is the C99 draft's list.
        self.make_reserved_names('''
           auto      enum      restrict  unsigned
           break     extern    return    void
           case      float     short     volatile
           char      for       signed    while
           const     goto      sizeof    _Bool
           continue  if        static    _Complex
           default   inline    struct    _Imaginary
           do        int       switch
           double    long      typedef
           else      register  union
           ''')


def c_string_constant(s, force_quote=False):
    '''Returns EITHER a " "-delimited string literal for C
               OR a { }-delimited array of chars.
    '''
    def char_repr(c):
        if c in '\\"': return '\\' + c
        if ' ' <= c < '\x7F': return c
        return '\\%03o' % ord(c)
    def line_repr(s):
        return ''.join([char_repr(c) for c in s])

    if len(s) < 64:
        return '"%s"' % line_repr(s)

    elif len(s) < 1024 or force_quote:
        lines = ['"']
        for i in range(0, len(s), 32):
            lines.append(line_repr(s[i:i+32]))
        lines[-1] += '"'
        return '\\\n'.join(lines)

    else:
        lines = []
        for i in range(0, len(s), 20):
            lines.append(','.join([str(ord(c)) for c in s[i:i+20]]))
        return '{\n%s}' % ',\n'.join(lines)


def gen_assignments(assignments):
    # Generate a sequence of assignments that is possibly reordered
    # to avoid clashes -- i.e. do the equivalent of a tuple assignment,
    # reading all sources first, writing all targets next, but optimized

    allsources = []
    src2dest = {}
    types = {}
    assignments = list(assignments)
    for typename, dest, src in assignments:
        if src != dest:   # ignore 'v=v;'
            allsources.append(src)
            src2dest.setdefault(src, []).append(dest)
            types[dest] = typename

    for starting in allsources:
        # starting from some starting variable, follow a chain of assignments
        #     'vn=vn-1; ...; v3=v2; v2=v1; v1=starting;'
        v = starting
        srcchain = []
        while src2dest.get(v):
            srcchain.append(v)
            v = src2dest[v].pop(0)
            if v == starting:
                break    # loop
        if not srcchain:
            continue   # already done in a previous chain
        srcchain.reverse()   # ['vn-1', ..., 'v2', 'v1', 'starting']
        code = []
        for pair in zip([v] + srcchain[:-1], srcchain):
            code.append('%s = %s;' % pair)
        if v == starting:
            # assignment loop 'starting=vn-1; ...; v2=v1; v1=starting;'
            typename = types[starting]
            tmpdecl = cdecl(typename, 'tmp')
            code.insert(0, '{ %s = %s;' % (tmpdecl, starting))
            code[-1] = '%s = tmp; }' % (srcchain[-2],)
        yield ' '.join(code)

# logging

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("c")
py.log.setconsumer("c", ansi_log)
