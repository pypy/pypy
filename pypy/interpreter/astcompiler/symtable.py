"""
Symbol tabling building.
"""

from pypy.interpreter.astcompiler import ast, misc
from pypy.interpreter.pyparser.error import SyntaxError

# These are for internal use only:
SYM_BLANK = 0
SYM_GLOBAL = 1
SYM_ASSIGNED = 2 # Or deleted actually.
SYM_PARAM = 2 << 1
SYM_USED = 2 << 2
SYM_BOUND = (SYM_PARAM | SYM_ASSIGNED)

# codegen.py actually deals with these:
SCOPE_UNKNOWN = 0
SCOPE_GLOBAL_IMPLICIT = 1
SCOPE_GLOBAL_EXPLICIT = 2
SCOPE_LOCAL = 3
SCOPE_FREE = 4
SCOPE_CELL = 5


class Scope(object):

    can_be_optimized = False

    def __init__(self, name, lineno=0, col_offset=0):
        self.lineno = lineno
        self.col_offset = col_offset
        self.parent = None
        self.name = name
        self.locals_fully_known = False
        self.symbols = None
        self.roles = {}
        self.varnames = []
        self.children = []
        self.free_vars = []
        self.temp_name_counter = 1
        self.has_exec = False
        self.has_free = False
        self.child_has_free = False
        self.nested = False

    def lookup(self, name):
        """Find the scope of identifier 'name'."""
        return self.symbols.get(self.mangle(name), SCOPE_UNKNOWN)

    def lookup_role(self, name):
        return self.roles.get(self.mangle(name), SYM_BLANK)

    def new_temporary_name(self):
        """Return the next temporary name.

        This must be in sync with PythonCodeGenerator's counter.
        """
        self.note_symbol("_[%d]" % (self.temp_name_counter,), SYM_ASSIGNED)
        self.temp_name_counter += 1

    def note_symbol(self, identifier, role):
        """Record that identifier occurs in this scope."""
        mangled = self.mangle(identifier)
        new_role = role
        if mangled in self.roles:
            old_role = self.roles[mangled]
            if old_role & SYM_PARAM and role & SYM_PARAM:
                err = "duplicate argument '%s' in function definition" % \
                    (identifier,)
                raise SyntaxError(err, self.lineno, self.col_offset)
            new_role |= old_role
        self.roles[mangled] = new_role
        if role & SYM_PARAM:
            self.varnames.append(mangled)
        return mangled

    def note_yield(self, yield_node):
        """Called when a yield is found."""
        raise SyntaxError("'yield' outside function", yield_node.lineno,
                          yield_node.col_offset)

    def note_return(self, ret):
        """Called when a return statement is found."""
        raise SyntaxError("return outside function", ret.lineno,
                          ret.col_offset)

    def note_exec(self, exc):
        """Called when an exec statement is found."""
        self.has_exec = True

    def note_import_star(self, imp):
        """Called when a start import is found."""
        pass

    def mangle(self, name):
        if self.parent:
            return self.parent.mangle(name)
        else:
            return name

    def add_child(self, child_scope):
        """Note a new child scope."""
        child_scope.parent = self
        self.children.append(child_scope)

    def _finalize_name(self, name, flags, local, bound, free, globs):
        """Decide on the scope of a name."""
        if flags & SYM_GLOBAL:
            if flags & SYM_PARAM:
                err = "name '%s' is both local and global" % (name,)
                raise SyntaxError(err, self.lineno, self.col_offset)
            self.symbols[name] = SCOPE_GLOBAL_EXPLICIT
            globs[name] = None
            if bound:
                try:
                    del bound[name]
                except KeyError:
                    pass
        elif flags & SYM_BOUND:
            self.symbols[name] = SCOPE_LOCAL
            local[name] = None
            try:
                del globs[name]
            except KeyError:
                pass
        elif bound and name in bound:
            self.symbols[name] = SCOPE_FREE
            self.free_vars.append(name)
            free[name] = None
            self.has_free = True
        elif name in globs:
            self.symbols[name] = SCOPE_GLOBAL_IMPLICIT
        else:
            if self.nested:
                self.has_free = True
            self.symbols[name] = SCOPE_GLOBAL_IMPLICIT

    def _pass_on_bindings(self, local, bound, globs, new_bound, new_globs):
        """Allow child scopes to see names bound here and in outer scopes."""
        new_globs.update(globs)
        if bound:
            new_bound.update(bound)

    def _finalize_cells(self, free):
        """Hook for FunctionScope."""
        pass

    def _check_optimization(self):
        pass

    _hide_bound_from_nested_scopes = False

    def finalize(self, bound, free, globs):
        """Enter final bookeeping data in to self.symbols."""
        self.symbols = {}
        local = {}
        new_globs = {}
        new_bound = {}
        new_free = {}
        if self._hide_bound_from_nested_scopes:
            self._pass_on_bindings(local, bound, globs, new_bound, new_globs)
        for name, flags in self.roles.iteritems():
            self._finalize_name(name, flags, local, bound, free, globs)
        if not self._hide_bound_from_nested_scopes:
            self._pass_on_bindings(local, bound, globs, new_bound, new_globs)
        child_frees = {}
        for child in self.children:
            # Symbol dictionaries are copied to avoid having child scopes
            # pollute each other's.
            child_free = new_free.copy()
            child.finalize(new_bound.copy(), child_free, new_globs.copy())
            child_frees.update(child_free)
            if child.has_free or child.child_has_free:
                self.child_has_free = True
        new_free.update(child_frees)
        self._finalize_cells(new_free)
        for name in new_free:
            try:
                role_here = self.roles[name]
            except KeyError:
                if name in bound:
                    self.symbols[name] = SCOPE_FREE
                    self.free_vars.append(name)
            else:
                if role_here & (SYM_BOUND | SYM_GLOBAL) and \
                        self._hide_bound_from_nested_scopes:
                    # This happens when a class level attribute or method has
                    # the same name as a free variable passing through the class
                    # scope.  We add the name to the class scope's list of free
                    # vars, so it will be passed through by the interpreter, but
                    # we leave the scope alone, so it can be local on its own.
                    self.free_vars.append(name)
        self._check_optimization()
        free.update(new_free)


class ModuleScope(Scope):

    def __init__(self):
        Scope.__init__(self, "top")


class FunctionScope(Scope):

    can_be_optimized = True

    def __init__(self, name, lineno, col_offset):
        Scope.__init__(self, name, lineno, col_offset)
        self.has_variable_arg = False
        self.has_keywords_arg = False
        self.is_generator = False
        self.optimized = True
        self.return_with_value = False
        self.import_star = None
        self.bare_exec = None

    def note_yield(self, yield_node):
        if self.return_with_value:
            raise SyntaxError("'return' with argument inside generator",
                              self.ret.lineno, self.ret.col_offset)
        self.is_generator = True

    def note_return(self, ret):
        if ret.value:
            if self.is_generator:
                raise SyntaxError("'return' with argument inside generator",
                                  ret.lineno, ret.col_offset)
            self.return_with_value = True
            self.ret = ret

    def note_exec(self, exc):
        Scope.note_exec(self, exc)
        if not exc.globals:
            self.optimized = False
            self.bare_exec = exc

    def note_import_star(self, imp):
        self.optimized = False
        self.import_star = imp

    def note_variable_arg(self, vararg):
        self.has_variable_arg = True

    def note_keywords_arg(self, kwarg):
        self.has_keywords_arg = True

    def add_child(self, child_scope):
        Scope.add_child(self, child_scope)
        child_scope.nested = True

    def _pass_on_bindings(self, local, bound, globs, new_bound, new_globs):
        new_bound.update(local)
        Scope._pass_on_bindings(self, local, bound, globs, new_bound, new_globs)

    def _finalize_cells(self, free):
        for name, role in self.symbols.iteritems():
            if role == SCOPE_LOCAL and name in free:
                self.symbols[name] = SCOPE_CELL
                del free[name]

    def _check_optimization(self):
        if (self.has_free or self.child_has_free) and not self.optimized:
            err = None
            if self.child_has_free:
                trailer = "contains a nested function with free variables"
            else:
                trailer = "is a nested function"
            name = self.name
            if self.import_star:
                node = self.import_star
                if self.bare_exec:
                    err = "function '%s' uses import * and bare exec, " \
                        "which are illegal because it %s" % (name, trailer)
                else:
                    err = "import * is not allowed in function '%s' because " \
                        "it %s" % (name, trailer)
            elif self.bare_exec:
                node = self.bare_exec
                err = "unqualified exec is not allowed in function '%s' " \
                    "because it %s" % (name, trailer)
            else:
                raise AssertionError("unknown reason for unoptimization")
            raise SyntaxError(err, node.lineno, node.col_offset)
        self.locals_fully_known = self.optimized and not self.has_exec


class ClassScope(Scope):

    _hide_bound_from_nested_scopes = True

    def __init__(self, clsdef):
        Scope.__init__(self, clsdef.name, clsdef.lineno, clsdef.col_offset)

    def mangle(self, name):
        return misc.mangle(name, self.name)


class SymtableBuilder(ast.GenericASTVisitor):
    """Find symbol information from AST."""

    def __init__(self, space, module, compile_info):
        self.space = space
        self.module = module
        self.compile_info = compile_info
        self.scopes = {}
        self.scope = None
        self.stack = []
        top = ModuleScope()
        self.globs = top.roles
        self.push_scope(top, module)
        try:
            module.walkabout(self)
            top.finalize(None, {}, {})
        except SyntaxError, e:
            e.filename = compile_info.filename
            raise
        self.pop_scope()
        assert not self.stack

    def push_scope(self, scope, node):
        """Push a child scope."""
        if self.stack:
            self.stack[-1].add_child(scope)
        self.stack.append(scope)
        self.scopes[node] = scope
        # Convenience
        self.scope = scope

    def pop_scope(self):
        self.stack.pop()
        if self.stack:
            self.scope = self.stack[-1]
        else:
            self.scope = None

    def find_scope(self, scope_node):
        """Lookup the scope for a given AST node."""
        return self.scopes[scope_node]

    def implicit_arg(self, pos):
        """Note a implicit arg for implicit tuple unpacking."""
        name = ".%d" % (pos,)
        self.note_symbol(name, SYM_PARAM)

    def note_symbol(self, identifier, role):
        """Note the identifer on the current scope."""
        mangled = self.scope.note_symbol(identifier, role)
        if role & SYM_GLOBAL:
            if mangled in self.globs:
                role |= self.globs[mangled]
            self.globs[mangled] = role

    def visit_FunctionDef(self, func):
        self.note_symbol(func.name, SYM_ASSIGNED)
        # Function defaults and decorators happen in the outer scope.
        if func.args.defaults:
            self.visit_sequence(func.args.defaults)
        if func.decorators:
            self.visit_sequence(func.decorators)
        new_scope = FunctionScope(func.name, func.lineno, func.col_offset)
        self.push_scope(new_scope, func)
        func.args.walkabout(self)
        self.visit_sequence(func.body)
        self.pop_scope()

    def visit_Return(self, ret):
        self.scope.note_return(ret)
        ast.GenericASTVisitor.visit_Return(self, ret)

    def visit_ClassDef(self, clsdef):
        self.note_symbol(clsdef.name, SYM_ASSIGNED)
        if clsdef.bases:
            self.visit_sequence(clsdef.bases)
        self.push_scope(ClassScope(clsdef), clsdef)
        self.visit_sequence(clsdef.body)
        self.pop_scope()

    def visit_ImportFrom(self, imp):
        for alias in imp.names:
            if self._visit_alias(alias):
                self.scope.note_import_star(imp)

    def _visit_alias(self, alias):
        assert isinstance(alias, ast.alias)
        if alias.asname:
            store_name = alias.asname
        else:
            store_name = alias.name
            if store_name == "*":
                return True
            dot = store_name.find(".")
            if dot > 0:
                store_name = store_name[:dot]
        self.note_symbol(store_name, SYM_ASSIGNED)
        return False

    def visit_alias(self, alias):
        self._visit_alias(alias)

    def visit_Exec(self, exc):
        self.scope.note_exec(exc)
        ast.GenericASTVisitor.visit_Exec(self, exc)

    def visit_Yield(self, yie):
        self.scope.note_yield(yie)
        ast.GenericASTVisitor.visit_Yield(self, yie)

    def visit_Global(self, glob):
        for name in glob.names:
            old_role = self.scope.lookup_role(name)
            if old_role & (SYM_USED | SYM_ASSIGNED):
                if old_role & SYM_ASSIGNED:
                    msg = "name '%s' is assigned to before global declaration" \
                        % (name,)
                else:
                    msg = "name '%s' is used prior to global declaration" % \
                        (name,)
                misc.syntax_warning(self.space, msg, self.compile_info.filename,
                                    glob.lineno, glob.col_offset)
            self.note_symbol(name, SYM_GLOBAL)

    def visit_Lambda(self, lamb):
        if lamb.args.defaults:
            self.visit_sequence(lamb.args.defaults)
        new_scope = FunctionScope("lambda", lamb.lineno, lamb.col_offset)
        self.push_scope(new_scope, lamb)
        lamb.args.walkabout(self)
        lamb.body.walkabout(self)
        self.pop_scope()

    def visit_GeneratorExp(self, genexp):
        outer = genexp.generators[0]
        assert isinstance(outer, ast.comprehension)
        outer.iter.walkabout(self)
        new_scope = FunctionScope("genexp", genexp.lineno, genexp.col_offset)
        self.push_scope(new_scope, genexp)
        self.implicit_arg(0)
        outer.target.walkabout(self)
        if outer.ifs:
            self.visit_sequence(outer.ifs)
        self.visit_sequence(genexp.generators[1:])
        genexp.elt.walkabout(self)
        self.pop_scope()

    def visit_ListComp(self, lc):
        self.scope.new_temporary_name()
        ast.GenericASTVisitor.visit_ListComp(self, lc)

    def visit_With(self, wih):
        self.scope.new_temporary_name()
        if wih.optional_vars:
            self.scope.new_temporary_name()
        ast.GenericASTVisitor.visit_With(self, wih)

    def visit_arguments(self, arguments):
        scope = self.scope
        assert isinstance(scope, FunctionScope) # Annotator hint.
        if arguments.args:
            self._handle_params(arguments.args, True)
        if arguments.vararg:
            self.note_symbol(arguments.vararg, SYM_PARAM)
            scope.note_variable_arg(arguments.vararg)
        if arguments.kwarg:
            self.note_symbol(arguments.kwarg, SYM_PARAM)
            scope.note_keywords_arg(arguments.kwarg)
        if arguments.args:
            self._handle_nested_params(arguments.args)

    def _handle_params(self, params, is_toplevel):
        for i in range(len(params)):
            arg = params[i]
            if isinstance(arg, ast.Name):
                self.note_symbol(arg.id, SYM_PARAM)
            elif isinstance(arg, ast.Tuple):
                # Tuple unpacking in the argument list.  Add a secret variable
                # name to recieve the tuple with.
                if is_toplevel:
                    self.implicit_arg(i)
            else:
                raise AssertionError("unknown parameter type")
        if not is_toplevel:
            self._handle_nested_params(params)

    def _handle_nested_params(self, params):
        for param in params:
            if isinstance(param, ast.Tuple):
                self._handle_params(param.elts, False)

    def visit_Name(self, name):
        if name.ctx == ast.Load:
            role = SYM_USED
        else:
            role = SYM_ASSIGNED
        self.note_symbol(name.id, role)
