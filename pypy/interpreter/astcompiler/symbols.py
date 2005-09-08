"""Module symbol-table generator"""

from pypy.interpreter.astcompiler import ast
from pypy.interpreter.astcompiler.consts import SC_LOCAL, SC_GLOBAL, \
    SC_FREE, SC_CELL, SC_UNKNOWN, SC_REALLY_GLOBAL
from pypy.interpreter.astcompiler.misc import mangle
from pypy.interpreter.pyparser.error import SyntaxError
import types


import sys

MANGLE_LEN = 256

class Scope:
    # XXX how much information do I need about each name?
    def __init__(self, name, module, klass=None):
        self.name = name
        self.module = module
        self.defs = {}
        self.uses = {}
        self.globals = {}
        self.params = {}
        self.frees = {}
        self.cells = {}
        self.children = []
        # nested is true if the class could contain free variables,
        # i.e. if it is nested within another function.
        self.nested = 0
        self.generator = 0
        self.klass = None
        if klass is not None:
            for i in range(len(klass)):
                if klass[i] != '_':
                    self.klass = klass[i:]
                    break

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.name)

    def mangle(self, name):
        if self.klass is None:
            return name
        return mangle(name, self.klass)

    def add_def(self, name):
        self.defs[self.mangle(name)] = 1

    def add_use(self, name):
        self.uses[self.mangle(name)] = 1

    def add_global(self, name):
        name = self.mangle(name)
        if name in self.uses or name in self.defs:
            pass # XXX warn about global following def/use
        if name in self.params:
            raise SyntaxError, "%s in %s is global and parameter" % \
                  (name, self.name)
        self.globals[name] = 1
        self.module.add_def(name)

    def add_param(self, name):
        name = self.mangle(name)
        self.defs[name] = 1
        self.params[name] = 1

    def get_names(self):
        d = {}
        d.update(self.defs)
        d.update(self.uses)
        d.update(self.globals)
        return d.keys()

    def add_child(self, child):
        self.children.append(child)

    def get_children(self):
        return self.children

    def DEBUG(self):
        print >> sys.stderr, self.name, self.nested and "nested" or ""
        print >> sys.stderr, "\tglobals: ", self.globals
        print >> sys.stderr, "\tcells: ", self.cells
        print >> sys.stderr, "\tdefs: ", self.defs
        print >> sys.stderr, "\tuses: ", self.uses
        print >> sys.stderr, "\tfrees:", self.frees

    def check_name(self, name):
        """Return scope of name.

        The scope of a name could be LOCAL, GLOBAL, FREE, or CELL.
        """
        if name in self.globals:
            return SC_REALLY_GLOBAL
        if name in self.cells:
            return SC_CELL
        if name in self.defs:
            return SC_LOCAL
        if self.nested and (name in self.frees or
                            name in self.uses):
            return SC_FREE
        if self.nested:
            return SC_UNKNOWN
        else:
            return SC_GLOBAL

    def get_free_vars(self):
        if not self.nested:
            return []
        free = {}
        free.update(self.frees)
        for name in self.uses.keys():
            if not (name in self.defs or
                    name in self.globals):
                free[name] = 1
        return free.keys()

    def handle_children(self):
        for child in self.children:
            frees = child.get_free_vars()
            globals = self.add_frees(frees)
            for name in globals:
                child.force_global(name)

    def force_global(self, name):
        """Force name to be global in scope.

        Some child of the current node had a free reference to name.
        When the child was processed, it was labelled a free
        variable.  Now that all its enclosing scope have been
        processed, the name is known to be a global or builtin.  So
        walk back down the child chain and set the name to be global
        rather than free.

        Be careful to stop if a child does not think the name is
        free.
        """
        self.globals[name] = 1
        if name in self.frees:
            del self.frees[name]
        for child in self.children:
            if child.check_name(name) == SC_FREE:
                child.force_global(name)

    def add_frees(self, names):
        """Process list of free vars from nested scope.

        Returns a list of names that are either 1) declared global in the
        parent or 2) undefined in a top-level parent.  In either case,
        the nested scope should treat them as globals.
        """
        child_globals = []
        for name in names:
            sc = self.check_name(name)
            if self.nested:
                if sc == SC_UNKNOWN or sc == SC_FREE \
                   or isinstance(self, ClassScope):
                    self.frees[name] = 1
                elif sc == SC_GLOBAL or sc == SC_REALLY_GLOBAL:
                    child_globals.append(name)
                elif isinstance(self, FunctionScope) and sc == SC_LOCAL:
                    self.cells[name] = 1
                elif sc != SC_CELL:
                    child_globals.append(name)
            else:
                if sc == SC_LOCAL:
                    self.cells[name] = 1
                elif sc != SC_CELL:
                    child_globals.append(name)
        return child_globals

    def get_cell_vars(self):
        return self.cells.keys()

class ModuleScope(Scope):

    def __init__(self):
        Scope.__init__(self, "global", self)

class FunctionScope(Scope):
    pass

class GenExprScope(Scope):
    __counter = 1

    def __init__(self, module, klass=None):
        i = self.__counter
        self.__counter += 1
        Scope.__init__(self, "generator expression<%d>"%i, module, klass)
        self.add_param('[outmost-iterable]')

    def get_names(self):
        keys = Scope.get_names()
        return keys

class LambdaScope(FunctionScope):
    __counter = 1

    def __init__(self, module, klass=None):
        i = self.__counter
        self.__counter += 1
        Scope.__init__(self, "lambda.%d" % i, module, klass)

class ClassScope(Scope):

    def __init__(self, name, module):
        Scope.__init__(self, name, module, name)

class SymbolVisitor(ast.ASTVisitor):
    def __init__(self, space):
        self.space = space
        self.scopes = {}
        self.klass = None
        self.scope_stack = []
        self.assign_stack = [ False ]

    def cur_assignment(self):
        return self.assign_stack[-1]

    def push_assignment(self, val ):
        self.assign_stack.append( val )

    def pop_assignment(self):
        self.assign_stack.pop()

    def push_scope( self, scope ):
        self.scope_stack.append( scope )

    def pop_scope( self ):
        self.scope_stack.pop()

    def cur_scope( self ):
        return self.scope_stack[-1]
    
    # node that define new scopes

    def visitModule(self, node):
        scope = self.module = self.scopes[node] = ModuleScope()
        self.push_scope(scope)
        node.node.accept(self)
        self.pop_scope()

    visitExpression = visitModule

    def visitFunction(self, node):
        parent = self.cur_scope()
        if node.decorators:
            node.decorators.accept(self)
        parent.add_def(node.name)
        for n in node.defaults:
            n.accept( self )
        scope = FunctionScope(node.name, self.module, self.klass)
        if parent.nested or isinstance(parent, FunctionScope):
            scope.nested = 1
        self.scopes[node] = scope
        self._do_args(scope, node.argnames)
        self.push_scope( scope )
        node.code.accept(self )
        self.pop_scope()
        self.handle_free_vars(scope, parent)

    def visitGenExpr(self, node ):
        parent = self.cur_scope()
        scope = GenExprScope(self.module, self.klass);
        if parent.nested or isinstance(parent, FunctionScope) \
                or isinstance(parent, GenExprScope):
            scope.nested = 1

        self.scopes[node] = scope
        self.push_scope(scope)
        node.code.accept(self)
        self.pop_scope()

        self.handle_free_vars(scope, parent)

    def visitGenExprInner(self, node ):
        #scope = self.cur_scope()
        for genfor in node.quals:
            genfor.accept( self )

        node.expr.accept( self )

    def visitGenExprFor(self, node ):
        self.push_assignment( True )
        node.assign.accept(self)
        self.pop_assignment()
        node.iter.accept(self )
        for if_ in node.ifs:
            if_.accept( self )

    def visitGenExprIf(self, node ):
        node.test.accept( self )

    def visitLambda(self, node ):
        # Lambda is an expression, so it could appear in an expression
        # context where assign is passed.  The transformer should catch
        # any code that has a lambda on the left-hand side.
        assert not self.cur_assignment()
        parent = self.cur_scope()
        for n in node.defaults:
            n.accept( self )
        scope = LambdaScope(self.module, self.klass)
        if parent.nested or isinstance(parent, FunctionScope):
            scope.nested = 1
        self.scopes[node] = scope
        self._do_args(scope, node.argnames)
        self.push_scope(scope)
        node.code.accept(self)
        self.pop_scope()
        self.handle_free_vars(scope, parent)

    def _do_args(self, scope, args):
        for arg in args:
            if isinstance( arg, ast.AssName ):
                scope.add_param( arg.name )
            elif isinstance( arg, ast.AssTuple ):
                self._do_args( scope, arg.flatten() )
            else:
                raise TypeError( "Argument list contains %s of type %s" % (arg, type(arg) ) )

    def handle_free_vars(self, scope, parent):
        parent.add_child(scope)
        scope.handle_children()

    def visitClass(self, node):
        parent = self.cur_scope()
        parent.add_def(node.name)
        for n in node.bases:
            n.accept(self)
        scope = ClassScope(node.name, self.module)
        if parent.nested or isinstance(parent, FunctionScope):
            scope.nested = 1
        if node.doc is not None:
            scope.add_def('__doc__')
        scope.add_def('__module__')
        self.scopes[node] = scope
        prev = self.klass
        self.klass = node.name
        self.push_scope( scope )
        node.code.accept(self)
        self.pop_scope()
        self.klass = prev
        self.handle_free_vars(scope, parent)

    # name can be a def or a use

    # XXX a few calls and nodes expect a third "assign" arg that is
    # true if the name is being used as an assignment.  only
    # expressions contained within statements may have the assign arg.

    def visitName(self, node ):
        scope = self.cur_scope()
        if self.cur_assignment():
            scope.add_def(node.varname)
        else:
            scope.add_use(node.varname)

    # operations that bind new names

    def visitFor(self, node ):
        self.push_assignment( True )
        node.assign.accept( self )
        self.pop_assignment()
        node.list.accept( self )
        node.body.accept( self )
        if node.else_:
            node.else_.accept( self )

    def visitFrom(self, node ):
        scope = self.cur_scope()
        for name, asname in node.names:
            if name == "*":
                continue
            scope.add_def(asname or name)

    def visitImport(self, node ):
        scope = self.cur_scope()
        for name, asname in node.names:
            i = name.find(".")
            if i > -1:
                name = name[:i]
            scope.add_def(asname or name)

    def visitGlobal(self, node ):
        scope = self.cur_scope()
        for name in node.names:
            scope.add_global(name)

    def visitAssign(self, node ):
        """Propagate assignment flag down to child nodes.

        The Assign node doesn't itself contains the variables being
        assigned to.  Instead, the children in node.nodes are visited
        with the assign flag set to true.  When the names occur in
        those nodes, they are marked as defs.

        Some names that occur in an assignment target are not bound by
        the assignment, e.g. a name occurring inside a slice.  The
        visitor handles these nodes specially; they do not propagate
        the assign flag to their children.
        """
        self.push_assignment( True )
        for n in node.nodes:
            n.accept( self )
        self.pop_assignment()
        node.expr.accept( self )

    def visitAssName(self, node ):
        scope = self.cur_scope()
        scope.add_def(node.name)

    def visitAssAttr(self, node ):
        self.push_assignment( False )
        node.expr.accept( self )
        self.pop_assignment()

    def visitSubscript(self, node ):
        self.push_assignment( False )
        node.expr.accept( self )
        for n in node.subs:
            n.accept( self )
        self.pop_assignment()

    def visitSlice(self, node ):
        self.push_assignment( False )
        node.expr.accept( self )
        if node.lower:
            node.lower.accept( self )
        if node.upper:
            node.upper.accept( self )
        self.pop_assignment()

    def visitAugAssign(self, node ):
        # If the LHS is a name, then this counts as assignment.
        # Otherwise, it's just use.
        node.node.accept( self )
        if isinstance(node.node, ast.Name):
            self.push_assignment( True ) # XXX worry about this
            node.node.accept( self )
            self.pop_assignment()
        node.expr.accept( self )

    # prune if statements if tests are false

    def visitIf(self, node ):
        for test, body in node.tests:
            if isinstance(test, ast.Const):
                if not self.space.is_true(test.value):
                    continue
            test.accept( self )
            body.accept( self )
        if node.else_:
            node.else_.accept( self )

    # a yield statement signals a generator

    def visitYield(self, node ):
        scope = self.cur_scope()
        scope.generator = 1
        node.value.accept( self )

def sort(l):
    l = l[:]
    l.sort()
    return l

def list_eq(l1, l2):
    return sort(l1) == sort(l2)

if __name__ == "__main__":
    import sys
    from pypy.interpreter.astcompiler import parseFile, walk
    import symtable

    def get_names(syms):
        return [s for s in [s.get_name() for s in syms.get_symbols()]
                if not (s.startswith('_[') or s.startswith('.'))]

    for file in sys.argv[1:]:
        print file
        f = open(file)
        buf = f.read()
        f.close()
        syms = symtable.symtable(buf, file, "exec")
        mod_names = get_names(syms)
        tree = parseFile(file)
        s = SymbolVisitor()
        walk(tree, s)

        # compare module-level symbols
        names2 = s.scopes[tree].get_names()

        if not list_eq(mod_names, names2):
            print
            print "oops", file
            print sort(mod_names)
            print sort(names2)
            sys.exit(-1)

        d = {}
        d.update(s.scopes)
        del d[tree]
        scopes = d.values()
        del d

        for s in syms.get_symbols():
            if s.is_namespace():
                l = [sc for sc in scopes
                     if sc.name == s.get_name()]
                if len(l) > 1:
                    print "skipping", s.get_name()
                else:
                    if not list_eq(get_names(s.get_namespace()),
                                   l[0].get_names()):
                        print s.get_name()
                        print sort(get_names(s.get_namespace()))
                        print sort(l[0].get_names())
                        sys.exit(-1)
