# some analysis of global imports

"""
The idea:
compile a module's source text and walk recursively
through the code objects. Find out which globals
are used.
Then examine each 'import *' by importing that module
and looking for those globals.
Replace the 'import *' by the list found.
More advanced: If the new import has more than, say, 5 entries,
rewrite the import to use module.name throughout the source.
"""

import dis, cStringIO, sys

def disasm(code):
    hold = sys.stdout
    try:
        sys.stdout = cStringIO.StringIO()
        dis.dis(code)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = hold

def offset2lineno(c, stopat):
    tab = c.co_lnotab
    line = c.co_firstlineno
    addr = 0
    for i in range(0, len(tab), 2):
        addr = addr + ord(tab[i])
        if addr > stopat:
            break
        line = line + ord(tab[i+1])
    return line

def globalsof(code, globrefs=None, stars=None, globals=None):
    names = code.co_names
    vars = code.co_varnames
    if globrefs is None: globrefs = {}
    if stars is None: stars = [] # do stars in order
    if globals is None: globals = {}
    in_seq = False
    for line in disasm(code).split('\n'):
        words = line.split()
        ofs = -1
        while words and words[0].isdigit():
            ofs = int(words.pop(0))
        if not words:
            continue
        op = words[0]
        if op == 'LOAD_GLOBAL':
            name = words[-1][1:-1] # omit ()
            refs = globrefs.setdefault(name, {})
            offsets = refs.setdefault(code, [])
            offsets.append(ofs)
        elif op == 'IMPORT_NAME':
            in_seq = True
            imp_module = words[-1][1:-1]
            imp_what = None
        elif op == 'IMPORT_FROM':
            in_seq = True
            imp_what = words[-1][1:-1]
        elif op == 'STORE_NAME':
            # we are not interested in local imports, which
            # would generate a STORE_FAST
            name = words[-1][1:-1]
            if in_seq:
                globals[name] = imp_what, imp_module
                in_seq = False
            else:
                globals[name] = None, None
        elif op == 'IMPORT_STAR':
            stars.append( (imp_module, ofs) )
            in_seq = False
        else:
            in_seq = False
    return globrefs, stars, globals

def allglobalsof(code):
    globrefs = {}
    stars = []
    globals = {}
    seen = {}
    if type(code) is str:
        fname = code
        code = compile(file(fname).read(), fname, 'exec')
    todo = [code]
    while todo:
        code = todo.pop(0)
        globalsof(code, globrefs, stars, globals)
        seen[code] = True
        for const in code.co_consts:
            if type(const) is type(code) and const not in seen:
                todo.append(const)
    return globrefs, stars, globals

class Analyser:
    def __init__(self, fname):
        self.fname = fname
        self.globrefs, self.stars, self.globals = allglobalsof(fname)
        self.starimports = []

    def get_unknown_globals(self):
        from __builtin__ import __dict__ as bltin
        ret = [name for name in self.globrefs.keys()
               if name not in bltin and name not in self.globals]
        return ret

    def get_from_star(self, modname):
        dic = {}
        exec "from %s import *" % modname in dic
        return dic
    
    def resolve_star_imports(self):
        implicit = {}
        which = {}
        for star, ofs in self.stars:
            which[star] = []
            for key in self.get_from_star(star).keys():
                implicit[key] = star
        # sort out in which star import we find what.
        # note that we walked star imports in order,
        # so we are sure to resolve ambiguities correctly.
        for name in self.get_unknown_globals():
            mod = implicit[name]
            which[mod].append(name)
        imps = []
        for star, ofs in self.stars:
            imps.append( (ofs, star, which[star]) )
        self.starimports = imps
        