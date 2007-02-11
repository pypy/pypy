"""Module symbol-table generator"""

from pypy.interpreter.astcompiler import ast
from pypy.interpreter.astcompiler.consts import SC_LOCAL, SC_GLOBAL, \
    SC_FREE, SC_CELL, SC_UNKNOWN, SC_DEFAULT
from pypy.interpreter.astcompiler.misc import mangle, Counter
from pypy.interpreter.pyparser.error import SyntaxError
from pypy.interpreter import gateway

import sys


# the 'role' of variables records how the variable is
# syntactically used in a given scope.
ROLE_NONE     = ' '
ROLE_USED     = 'U'    # used only
ROLE_DEFINED  = 'D'    # defined (i.e. assigned to) in the current scope
ROLE_GLOBAL   = 'G'    # marked with the 'global' keyword in the current scope
ROLE_PARAM    = 'P'    # function parameter


class Scope:
    bare_exec = False
    import_star = False

    def __init__(self, name, parent):
        self.name = name
        self.varroles = {}         # {variable: role}
        self.children = []         # children scopes
        self.varscopes = None      # initialized by build_var_scopes()
        self.freevars = {}         # vars to show up in the code object's
                                   #   co_freevars.  Note that some vars may
                                   #   be only in this dict and not in
                                   #   varscopes; see need_passthrough_name()
        self.parent = parent
        if parent is not None:
            parent.children.append(self)

    def mangle(self, name):
        if self.parent is None:
            return name
        else:
            return self.parent.mangle(name)

    def locals_fully_known(self):
        return not self.bare_exec and not self.import_star

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.name)

    def add_use(self, name):
        name = self.mangle(name)
        if name not in self.varroles:
            self.varroles[name] = ROLE_USED

    def add_def(self, name):
        name = self.mangle(name)
        if self.varroles.get(name, ROLE_USED) == ROLE_USED:
            self.varroles[name] = ROLE_DEFINED

    def add_global(self, name):
        name = self.mangle(name)
        prevrole = self.varroles.get(name, ROLE_NONE)
        self.varroles[name] = ROLE_GLOBAL
        return prevrole

    def add_return(self, node):
        raise SyntaxError("'return' outside function")

    def add_yield(self):
        raise SyntaxError("'yield' outside function")

    def DEBUG(self):
        print >> sys.stderr, self
        print >> sys.stderr, "\troles:  ", self.varroles
        print >> sys.stderr, "\tscopes: ", self.varscopes

    def build_var_scopes(self, names_from_enclosing_funcs):
        """Build the varscopes dictionary of this scope and all children.

        The names_from_enclosing_funcs are the names that come from
        enclosing scopes.  It is a dictionary {name: source_function_scope},
        where the source_function_scope might be None to mean 'from the
        global scope'.  The whole names_from_enclosing_funcs can also be
        None, to mean that we don't know anything statically because of a
        bare exec or import *.

        A call to build_var_scopes() that uses a variable from an enclosing
        scope must patch the varscopes of that enclosing scope, to make the
        variable SC_CELL instead of SC_LOCAL, as well as the intermediate
        scopes, to make the variable SC_FREE in them.
        """
        newnames = {}      # new names that this scope potentially exports
                           # to its children (if it is a FunctionScope)
        self.varscopes = {}
        for name, role in self.varroles.items():
            if role == ROLE_USED:
                # where does this variable come from?
                if names_from_enclosing_funcs is None:
                    msg = self.parent.get_ambiguous_name_msg(
                        "it contains a nested function using the "
                        "variable '%s'" % (name,))
                    raise SyntaxError(msg)
                if name in names_from_enclosing_funcs:
                    enclosingscope = names_from_enclosing_funcs[name]
                    if enclosingscope is None:
                        # it is a global var
                        scope = SC_GLOBAL
                    else:
                        if not self.locals_fully_known():
                            msg = self.get_ambiguous_name_msg(
                                "it is a nested function, so the origin of "
                                "the variable '%s' is ambiguous" % (name,))
                            raise SyntaxError(msg)
                        enclosingscope.varscopes[name] = SC_CELL
                        parent = self.parent
                        while parent is not enclosingscope:
                            parent.need_passthrough_name(name)
                            parent = parent.parent
                        self.freevars[name] = True
                        scope = SC_FREE
                else:
                    scope = SC_DEFAULT
                self._use_var()
            elif role == ROLE_GLOBAL:
                # a global var
                newnames[name] = None
                scope = SC_GLOBAL
            else:
                # a ROLE_DEFINED or ROLE_PARAM local var
                newnames[name] = self
                scope = SC_LOCAL
            self.varscopes[name] = scope
        # call build_var_scopes() on all the children
        names_enclosing_children = self.export_names_to_children(
            names_from_enclosing_funcs,
            newnames)
        for subscope in self.children:
            subscope.build_var_scopes(names_enclosing_children)

    def export_names_to_children(self, names_from_enclosing_funcs, newnames):
        # by default, scopes don't export names to their children
        # (only FunctionScopes do)
        return names_from_enclosing_funcs

    def need_passthrough_name(self, name):
        # make the 'name' pass through the 'self' scope, without showing
        # up in the normal way in the scope.  This case occurs when a
        # free variable is needed in some inner sub-scope, and comes from
        # some outer super-scope.  Hiding the name is needed for e.g. class
        # scopes, otherwise the name sometimes end up in the class __dict__.
        # Note that FunctionScope override this to *not* hide the name,
        # because users might expect it to show up in the function's locals
        # then...
        self.freevars[name] = True

    def _use_var(self):
        pass

    def get_ambiguous_name_msg(self, reason):
        if self.bare_exec:
            cause = "unqualified exec"
        elif self.import_star:
            cause = "import *"
        else:
            assert self.parent
            return self.parent.get_ambiguous_name_msg(reason)
        return "%s is not allowed in '%s' because %s" % (cause, self.name,
                                                         reason)

    def check_name(self, name):
        """Return scope of name.
        """
        return self.varscopes.get(name, SC_UNKNOWN)

    def get_free_vars_in_scope(self):
        # list the names of the free variables, giving them the name they
        # should have inside this scope
        result = []
        for name in self.freevars:
            if self.check_name(name) != SC_FREE:
                # it's not considered as a free variable within this scope,
                # but only a need_passthrough_name().  We need to hide the
                # name to avoid confusion with another potential use of the
                # name in the 'self' scope.
                name = hiddenname(name)
            result.append(name)
        return result

    def get_free_vars_in_parent(self):
        # list the names of the free variables, giving them the name they
        # should have in the parent scope
        result = []
        for name in self.freevars:
            if self.parent.check_name(name) not in (SC_FREE, SC_CELL):
                # it's not considered as a free variable in the parent scope,
                # but only a need_passthrough_name().  We need to hide the
                # name to avoid confusion with another potential use of the
                # name in the parent scope.
                name = hiddenname(name)
            result.append(name)
        return result

    def get_cell_vars(self):
        return [name for name, scope in self.varscopes.items()
                     if scope == SC_CELL]


class ModuleScope(Scope):

    def __init__(self):
        Scope.__init__(self, "global", None)

    def finished(self):
        self.build_var_scopes({})


class FunctionScope(Scope):
    generator = False
    return_with_arg = None     # or the node

    def add_param(self, name):
        name = self.mangle(name)
        if name in self.varroles:
            msg = "duplicate argument '%s' in function definition" % (name,)
            raise SyntaxError(msg)
        self.varroles[name] = ROLE_PARAM

    def add_return(self, node):
        if node.value is not None:
            # record the first 'return expr' that we see, for error checking
            if self.return_with_arg is None:
                self.return_with_arg = node

    def add_yield(self):
        self.generator = True

    def export_names_to_children(self, names_from_enclosing_funcs, newnames):
        if names_from_enclosing_funcs is None:
            return None
        if not self.locals_fully_known():
            return None
        d = names_from_enclosing_funcs.copy()
        d.update(newnames)
        return d

    def need_passthrough_name(self, name):
        # overrides Scope.need_passthrough_name(), see comments there
        if name not in self.varscopes:
            self.varscopes[name] = SC_FREE
            self.freevars[name] = True

    def _use_var(self):
        # some extra checks just for CPython compatibility -- the logic
        # of build_var_scopes() in symbols.py should be able to detect
        # all the cases that would really produce broken code, but CPython
        # insists on raising SyntaxError in some more cases
        if self._is_nested_function():
            if self.bare_exec:
                raise SyntaxError("for CPython compatibility, an unqualified "
                                  "exec is not allowed here")
            if self.import_star:
                raise SyntaxError("for CPython compatibility, import * "
                                  "is not allowed here")

    def _is_nested_function(self):
        scope = self.parent
        while scope is not None:
            if isinstance(scope, FunctionScope):
                return True
            scope = scope.parent
        return False


class GenExprScope(FunctionScope):
    _counter = Counter(1)

    def __init__(self, parent):
        i = GenExprScope._counter.next()
        FunctionScope.__init__(self, "generator expression<%d>" % i, parent)
        self.add_param('[outmost-iterable]')


class LambdaScope(FunctionScope):
    _counter = Counter(1)

    def __init__(self, parent):
        i = LambdaScope._counter.next()
        FunctionScope.__init__(self, "lambda.%d" % i, parent)


class ClassScope(Scope):

    def mangle(self, name):
        return mangle(name, self.name)


def hiddenname(name):
    return '.(%s)' % (name,)


app = gateway.applevel(r'''
def issue_warning(msg, filename, lineno):
    import warnings
    try:
        warnings.warn_explicit(msg, SyntaxWarning, filename, lineno,
                               None, None)
    except SyntaxWarning:
        raise SyntaxError(msg, filename, lineno)
''')

_issue_warning = app.interphook('issue_warning')
def issue_warning(space, msg, filename, lineno):
    _issue_warning(space, space.wrap(msg), space.wrap(filename),
                   space.wrap(lineno))

class SymbolVisitor(ast.ASTVisitor):
    def __init__(self, space):
        self.space = space
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
        scope = self.module = node.scope = ModuleScope()
        if node.w_doc is not None:
            scope.add_def('__doc__')
        self.push_scope(scope)
        node.node.accept(self)
        self.pop_scope()
        scope.finished()

    def visitExpression(self, node):
        scope = self.module = node.scope = ModuleScope()
        self.push_scope(scope)
        node.node.accept(self)
        self.pop_scope()
        scope.finished()

    def visitFunction(self, node):
        parent = self.cur_scope()
        if node.decorators:
            node.decorators.accept(self)
        parent.add_def(node.name)
        for n in node.defaults:
            n.accept( self )
        scope = FunctionScope(node.name, parent)
        node.scope = scope
        self._do_args(scope, node.argnames)
        self.push_scope( scope )
        node.code.accept(self )
        self.pop_scope()

    def visitExec(self, node):
        if not (node.globals or node.locals):
            parent = self.cur_scope()
            parent.bare_exec = True
        ast.ASTVisitor.visitExec(self, node)

    def visitGenExpr(self, node ):
        parent = self.cur_scope()
        scope = GenExprScope(parent)
        node.scope = scope
        self.push_scope(scope)
        node.code.accept(self)
        self.pop_scope()

    def visitGenExprInner(self, node ):
        for genfor in node.quals:
            genfor.accept( self )

        node.expr.accept( self )

    def visitGenExprFor(self, node ):
        self.push_assignment( True )
        node.assign.accept(self)
        self.pop_assignment()
        if node.is_outmost:
            curscope = self.cur_scope()
            self.pop_scope()
            node.iter.accept(self)     # in the parent scope
            self.push_scope(curscope)
        else:
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
        scope = LambdaScope(parent)
        node.scope = scope
        self._do_args(scope, node.argnames)
        self.push_scope(scope)
        node.code.accept(self)
        self.pop_scope()

    def _do_args(self, scope, args):
        for arg in args:
            if isinstance( arg, ast.AssName ):
                scope.add_param( arg.name )
            elif isinstance( arg, ast.AssTuple ):
                self._do_args( scope, arg.flatten() )
            else:
                #msg = "Argument list contains %s of type %s" % (arg, type(arg) )
                msg = "Argument list contains ASTNodes other than AssName or AssTuple"
                raise TypeError( msg )

    def visitClass(self, node):
        parent = self.cur_scope()
        parent.add_def(node.name)
        for n in node.bases:
            n.accept(self)
        scope = ClassScope(node.name, parent)
        if node.w_doc is not None:
            scope.add_def('__doc__')
        scope.add_def('__module__')
        node.scope = scope
        self.push_scope( scope )
        node.code.accept(self)
        self.pop_scope()

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
                scope.import_star = True
                continue
            scope.add_def(asname or name)

    def visitImport(self, node ):
        scope = self.cur_scope()
        for name, asname in node.names:
            i = name.find(".")
            if i >= 0:
                name = name[:i]
            scope.add_def(asname or name)

    def visitGlobal(self, node ):
        scope = self.cur_scope()
        for name in node.names:
            prevrole = scope.add_global(name)
            if prevrole == ROLE_PARAM:
                msg = "name '%s' is a function parameter and declared global"
                raise SyntaxError(msg % (name,))
            elif prevrole == ROLE_DEFINED:
                msg = "name '%s' is assigned to before global declaration"
                issue_warning(self.space, msg % (name,),
                              node.filename, node.lineno)
            elif prevrole == ROLE_USED:
                msg = "name '%s' is used prior to global declaration"
                issue_warning(self.space, msg % (name,),
                              node.filename, node.lineno)

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
        node.sub.accept( self )
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

    # a yield statement signals a generator

    def visitYield(self, node ):
        scope = self.cur_scope()
        scope.add_yield()
        node.value.accept( self )
        
    def visitReturn(self, node):
        scope = self.cur_scope()
        scope.add_return(node)
        if node.value is not None:
            node.value.accept(self)

    def visitCondExpr(self, node):
        issue_warning(self.space, "conditional expression",
                      node.filename, node.lineno)
        ast.ASTVisitor.visitCondExpr(self, node)

def sort(l):
    l = l[:]
    l.sort()
    return l

def list_eq(l1, l2):
    return sort(l1) == sort(l2)

    
if __name__ == "__main__":
    import sys
    from pypy.interpreter.astcompiler import parseFile
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
        tree.accept(s)

        # compare module-level symbols
        names2 = tree.scope.get_names()

        if not list_eq(mod_names, names2):
            print
            print "oops", file
            print sort(mod_names)
            print sort(names2)
            sys.exit(-1)

        d = {}
        # this part won't work anymore
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
