import sys
import opcode
import dis
import imp
import os
from sys import path, prefix

"""
so design goal:

i want to take a pile of source code and analyze each module for the
names it defines and the modules it imports and the names it uses from
them.

then i can find things like:

- things which are just plain not used anywhere
- things which are defined in one module and only used in another
- importing of names from modules where they are just imported from
  somewhere else
- cycles in the import graph
- unecessary imports

finding imports at top level is fairly easy, although the variety of
types of import statement can be baffling.  a mini reference:

import foo

->

LOAD_CONST None
IMPORT_NAME foo
STORE_NAME foo


import foo as bar

->

LOAD_CONST None
IMPORT_NAME foo
STORE_NAME bar

from foo import bar

->

LOAD_CONST  ('bar',)
IMPORT_NAME foo
IMPORT_FROM bar
STORE_NAME  bar
POP_TOP

from foo import bar, baz

->

LOAD_CONST  ('bar','baz')
IMPORT_NAME foo
IMPORT_FROM bar
STORE_NAME  bar
IMPORT_FROM baz
STORE_NAME  baz
POP_TOP

from foo.baz import bar

->

LOAD_CONST  ('bar',)
IMPORT_NAME foo.baz
IMPORT_FROM bar
STORE_NAME  bar
POP_TOP


import foo.bar

->

LOAD_CONST  None
IMPORT_NAME foo.bar
STORE_NAME  foo

(I hate this style)

there are other forms, but i don't support them (should hit an
assertion rather than silently fail).

"""

class System:
    def __init__(self):
        self.modules = {}
        self.pendingmodules = {}

class Scope(object):
    def __init__(self, parent=None):
        self.modvars = {} # varname -> absolute module name
        self.parent = parent
        self.varsources = {}

    def mod_for_name(self, name):
        if name in self.modvars:
            return self.modvars[name]
        elif self.parent is not None:
            return self.parent.mod_for_name(name)
        else:
            return None

    def var_source(self, name):
        if name in self.varsources:
            return self.varsources[name]
        elif self.parent is not None:
            return self.parent.var_source(name)
        else:
            return None, None
        

class Module(object):
    def __init__(self, system):
        self.system = system
        self._imports = {} # {modname:{name:was-it-used?}}
        self.definitions = []
        self.toplevelscope = Scope()
    def import_(self, modname):
        if modname not in self._imports:
            if modname not in self.system.modules:
                self.system.pendingmodules[modname] = None
            self._imports[modname] = {}
        return self._imports[modname]

def iteropcodes(codestring):
    n = len(codestring)
    i = 0
    while i < n:
        op = ord(codestring[i])
        i += 1
        oparg = None
        assert op != opcode.EXTENDED_ARG
        if op >= opcode.HAVE_ARGUMENT:
            oparg = ord(codestring[i]) + ord(codestring[i+1])*256
            i += 2
        yield op, oparg

STORE_DEREF = opcode.opmap["STORE_DEREF"]
STORE_FAST = opcode.opmap["STORE_FAST"]
STORE_GLOBAL = opcode.opmap["STORE_GLOBAL"]
STORE_NAME = opcode.opmap["STORE_NAME"]
IMPORT_NAME = opcode.opmap["IMPORT_NAME"]
IMPORT_FROM = opcode.opmap["IMPORT_FROM"]
LOAD_CONST = opcode.opmap["LOAD_CONST"]
LOAD_ATTR = opcode.opmap["LOAD_ATTR"]

LOAD_FAST = opcode.opmap["LOAD_FAST"]
LOAD_NAME = opcode.opmap["LOAD_NAME"]
LOAD_GLOBAL = opcode.opmap["LOAD_GLOBAL"]

MAKE_CLOSURE = opcode.opmap["MAKE_CLOSURE"]
MAKE_FUNCTION = opcode.opmap["MAKE_FUNCTION"]

POP_TOP = opcode.opmap['POP_TOP']

def process(r, codeob, scope, toplevel=False):
    opcodes = list(iteropcodes(codeob.co_code))

    i = 0

    codeobjs = []
    
    while i < len(opcodes):
        op, oparg = opcodes[i]
        
        if op == IMPORT_NAME:
            preop, preoparg = opcodes[i-1]
            assert preop == LOAD_CONST

            fromlist = codeob.co_consts[preoparg]

            modname = codeob.co_names[oparg]
            
            if fromlist is None:
                # this is the 'import foo' case
                r.import_(modname)

                postop, postoparg = opcodes[i+1]

                # ban 'import foo.bar' (it's dubious style anyway, imho)
                
                #assert not '.' in modname
                
                scope.modvars[codeob.co_names[postoparg]] = modname.split('.')[0]
                i += 1
            elif fromlist == ('*',):
                r.import_(modname)['*'] = False
            else:
                # ok, this is from foo import bar
                path = None
                for part in modname.split('.'):
                    path = [imp.find_module(part, path)[1]]
#                assert '.' not in codeob.co_names[oparg]
                i += 1
                vars = mods = None
                for f in fromlist:
                    op, oparg = opcodes[i]
                    assert op == IMPORT_FROM
                    assert codeob.co_names[oparg] == f
                    i += 1

                    try:
                        imp.find_module(f, path)
                    except ImportError:
                        assert mods is None
                        vars = True
                        r.import_(modname)[f] = False
                    else:
                        assert vars is None
                        mods = True
                        submod = modname + '.' + f
                        r.import_(submod)
                        
                    op, oparg = opcodes[i]

                    assert op in [STORE_NAME, STORE_FAST, STORE_DEREF, STORE_GLOBAL]

                    if mods is not None:
                        scope.modvars[codeob.co_names[oparg]] = submod
                    else:
                        scope.varsources[codeob.co_names[oparg]] = modname, f
                    i += 1
                op, oparg = opcodes[i]
                assert op == POP_TOP
        elif op == STORE_NAME and toplevel or op == STORE_GLOBAL:
            r.definitions.append(codeob.co_names[oparg])
        elif op == LOAD_ATTR:
            preop, preoparg = opcodes[i-1]
            if preop in [LOAD_NAME, LOAD_GLOBAL]:
                m = scope.mod_for_name(codeob.co_names[preoparg])
                if m:
                    r.import_(m)[codeob.co_names[oparg]] = True
            elif preop in [LOAD_FAST]:
                m = scope.mod_for_name(codeob.co_varnames[preoparg])
                if m:
                    r.import_(m)[codeob.co_names[oparg]] = True                
        elif op in [LOAD_NAME, LOAD_GLOBAL]:
            name = codeob.co_names[oparg]
            m, a = scope.var_source(name)
            if m:
                assert a in r.import_(m)
                r.import_(m)[a] = True
        elif op in [LOAD_FAST]:
            name = codeob.co_varnames[oparg]
            m, a = scope.var_source(name)
            if m:
                assert a in r.import_(m)
                r.import_(m)[a] = True
        elif op in [MAKE_FUNCTION, MAKE_CLOSURE]:
            preop, preoparg = opcodes[i-1]
            assert preop == LOAD_CONST
            codeobjs.append(codeob.co_consts[preoparg])
                
        i += 1
    for c in codeobjs:
        process(r, c, Scope(scope))

def process_module(dottedname, system):
    path = find_from_dotted_name(dottedname)
    if os.path.isdir(path):
        path += '/__init__.py'
    code = compile(open(path, "U").read(), '', 'exec')
    r = Module(system)

    try:
        process(r, code, r.toplevelscope, True)
    except ImportError, e:
        print "failed!", e
    else:
        assert dottedname not in system.pendingmodules

        system.modules[dottedname] = r
        
    return r

a = 1

def find_from_dotted_name(modname):
    path = None
    for part in modname.split('.'):
        path = [imp.find_module(part, path)[1]]
    return path[0]

def main(path):
    system = System()
    system.pendingmodules[path] = None
    while system.pendingmodules:
        path, d = system.pendingmodules.popitem()
        print len(system.pendingmodules), path
        if not path.startswith('pypy.') or path == 'pypy._cache':
            continue
        process_module(path, system)

if __name__=='__main__':
    main(*sys.argv[1:])
