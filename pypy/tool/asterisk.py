# some analysis of global imports

"""
The idea:
compile a module's source text and walk recursively
through the code objects. Find out which globals
are used.
Then examine each 'import *' by importing that module
and looking for those globals.
Replace the 'import *' by the list found.
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
    
def globalsof(code, globs=None):
    names = code.co_names
    vars = code.co_varnames
    if globs is None:
        globs = {}
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
            refs = globs.setdefault(name, {})
            offsets = refs.setdefault(code, [])
            offsets.append(ofs)
        elif op == 'IMPORT_NAME':
            impname = words[-1][1:-1]
        elif op == 'IMPORT_STAR':
            name = impname, '*'
            del impname
            refs = globs.setdefault(name, {})
            offsets = refs.setdefault(code, [])
            offsets.append(ofs)
    return globs

def allglobalsof(code):
    globs = {}
    seen = {}
    if type(code) is str:
        fname = code
        code = compile(file(fname).read(), fname, 'exec')
    todo = [code]
    while todo:
        code = todo.pop(0)
        globalsof(code, globs)
        seen[code] = True
        for const in code.co_consts:
            if type(const) is type(code) and const not in seen:
                todo.append(const)
    return globs

