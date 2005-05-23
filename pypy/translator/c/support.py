from pypy.translator.gensupp import NameManager

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


class CNameManager(NameManager):
    def __init__(self):
        NameManager.__init__(self)
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
