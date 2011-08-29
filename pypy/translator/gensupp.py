"""
Some support for genxxx implementations of source generators.
Another name could be genEric, but well...
"""

import sys

from pypy.objspace.flow.model import Block

# ordering the blocks of a graph by source position

def ordered_blocks(graph):
    # collect all blocks
    allblocks = []
    for block in graph.iterblocks():
            # first we order by offset in the code string
            if block.operations:
                ofs = block.operations[0].offset
            else:
                ofs = sys.maxint
            # then we order by input variable name or value
            if block.inputargs:
                txt = str(block.inputargs[0])
            else:
                txt = "dummy"
            allblocks.append((ofs, txt, block))
    allblocks.sort()
    #for ofs, txt, block in allblocks:
    #    print ofs, txt, block
    return [block for ofs, txt, block in allblocks]

# a unique list, similar to a list.
# append1 appends an object only if it is not there, already.

class UniqueList(list):
    def __init__(self, *args, **kwds):
        list.__init__(self, *args, **kwds)
        self.dic = {}

    def append1(self, arg):
        try:
            self.dic[arg]
        except KeyError:
            self.dic[arg] = 1
            list.append(self, arg)
        except TypeError: # not hashable
            if arg not in self:
                list.append(self, arg)

def builtin_base(obj):
    typ = type(obj)
    return builtin_type_base(typ)

def builtin_type_base(typ):
    from copy_reg import _HEAPTYPE
    while typ.__flags__&_HEAPTYPE:
        typ = typ.__base__
    return typ

def c_string(s):
    return '"%s"' % (s.replace('\\', '\\\\').replace('"', '\"'),)

def uniquemodulename(name, SEEN={}):
    # never reuse the same module name within a Python session!
    i = 0
    while True:
        i += 1
        result = '%s_%d' % (name, i)
        if result not in SEEN:
            SEEN[result] = True
            return result

# a translation table suitable for str.translate() to remove
# non-C characters from an identifier
C_IDENTIFIER = ''.join([(('0' <= chr(i) <= '9' or
                          'a' <= chr(i) <= 'z' or
                          'A' <= chr(i) <= 'Z') and chr(i) or '_')
                        for i in range(256)])

# a name manager knows about all global and local names in the
# program and keeps them disjoint. It provides ways to generate
# shorter local names with and without wrapping prefixes,
# while always keeping all globals visible.

class NameManager(object):
    def __init__(self, global_prefix='', number_sep='_'):
        self.seennames = {}
        self.scope = 0
        self.scopelist = []
        self.global_prefix = global_prefix
        self.number_sep = number_sep

    def make_reserved_names(self, txt):
        """add names to list of known names. If one exists already,
        then we raise an exception. This function should be called
        before generating any new names."""
        for name in txt.split():
            if name in self.seennames:
                raise NameError, "%s has already been seen!"
            self.seennames[name] = 1

    def _ensure_unique(self, basename):
        n = self.seennames.get(basename, 0)
        self.seennames[basename] = n+1
        if n:
            return self._ensure_unique('%s_%d' % (basename, n))
        return basename

    def uniquename(self, basename, with_number=None, bare=False, lenmax=50):
        basename = basename[:lenmax].translate(C_IDENTIFIER)
        n = self.seennames.get(basename, 0)
        self.seennames[basename] = n+1
        if with_number is None:
            with_number = basename in ('v', 'w_')
        fmt = '%%s%s%%d' % self.number_sep
        if with_number and not basename[-1].isdigit():
            fmt = '%s%d'
        if n != 0 or with_number:
            basename = self._ensure_unique(fmt % (basename, n))
        if bare:
            return basename, self.global_prefix + basename
        else:
            return self.global_prefix + basename

    def localScope(self, parent=None):
        ret = _LocalScope(self, parent)
        while ret.scope >= len(self.scopelist):
            self.scopelist.append({})
        return ret

class _LocalScope(object):
    """track local names without hiding globals or nested locals"""
    def __init__(self, glob, parent):
        self.glob = glob
        if not parent:
            parent = glob
        self.parent = parent
        self.mapping = {}
        self.usednames = {}
        self.scope = parent.scope + 1

    def uniquename(self, basename):
        basename = basename.translate(C_IDENTIFIER)
        glob = self.glob
        p = self.usednames.get(basename, 0)
        self.usednames[basename] = p+1
        namesbyscope = glob.scopelist[self.scope]
        namelist = namesbyscope.setdefault(basename, [])
        if p == len(namelist):
            namelist.append(glob.uniquename(basename))
        return namelist[p]

    def localname(self, name, wrapped=False):
        """modify and mangle local names"""
        if name in self.mapping:
            return self.mapping[name]
        scorepos = name.rfind("_")
        if name.startswith("v") and name[1:].isdigit():
            basename = ('v', 'w_') [wrapped]
        elif scorepos >= 0 and name[scorepos+1:].isdigit():
            basename = name[:scorepos]
            # for wrapped named things, prepend a w_
            # for other named things, prepend a l_.
            # XXX The latter is needed because tcc has a nasty parser bug that
            # produces errors if names co-incide with global typedefs,
            # if the type prefix is itself a typedef reference!
            # XXX report this bug to the tcc maintainer(s)
            # YYY drop this comment afterwards, but keep the code, it's better.
            basename = ("l_", "w_")[wrapped] + basename
        else:
            basename = name
        ret = self.uniquename(basename)
        self.mapping[name] = ret
        return ret

