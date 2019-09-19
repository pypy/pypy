"""Rewrite assertion AST to produce nice error messages"""
from __future__ import absolute_import, division, print_function
import ast
import itertools
import marshal
import sys

from ast_util import callbinrepr, format_explanation as _format_explanation


# pytest caches rewritten pycs in __pycache__.
if hasattr(sys, "pypy_version_info"):
    impl = "pypy"
elif sys.platform == "java":
    impl = "jython"
else:
    impl = "cpython"
ver = sys.version_info
PYTEST_TAG = "%s-%s%s-PYTEST" % (impl, ver[0], ver[1])
del ver, impl

PYC_EXT = ".py" + (__debug__ and "c" or "o")
PYC_TAIL = "." + PYTEST_TAG + PYC_EXT


if sys.version_info >= (3, 5):
    ast_Call = ast.Call
else:
    def ast_Call(a, b, c):
        return ast.Call(a, b, c, None, None)


def _write_pyc(state, co, source_stat, pyc):
    # Technically, we don't have to have the same pyc format as
    # (C)Python, since these "pycs" should never be seen by builtin
    # import. However, there's little reason deviate, and I hope
    # sometime to be able to use imp.load_compiled to load them. (See
    # the comment in load_module above.)
    import struct
    try:
        fp = open(pyc, "wb")
    except IOError:
        err = sys.exc_info()[1].errno
        state.trace("error writing pyc file at %s: errno=%s" % (pyc, err))
        # we ignore any failure to write the cache file
        # there are many reasons, permission-denied, __pycache__ being a
        # file etc.
        return False
    try:
        fp.write(imp.get_magic())
        mtime = int(source_stat.mtime)
        size = source_stat.size & 0xFFFFFFFF
        fp.write(struct.pack("<ll", mtime, size))
        marshal.dump(co, fp)
    finally:
        fp.close()
    return True


def rewrite_asserts(source, filename):
    """Parse the source code and rewrite asserts statements

    Returns a module object.
    """
    tree = ast.parse(source)
    AssertionRewriter(filename).run(tree)
    co = compile(tree, filename, 'exec')
    return co


def create_module(filename, co, pyc=None):
    """Create a module from a code object created by rewrite_asserts()"""
    mod = type(sys)(filename)
    mod.__file__ = co.co_filename
    if pyc is not None:
        mod.__cached__ = pyc
    mod.__loader__ = None
    exec(co, mod.__dict__)
    return mod


def _make_rewritten_pyc(state, source_stat, pyc, co):
    """Try to dump rewritten code to *pyc*."""
    import os
    if sys.platform.startswith("win"):
        # Windows grants exclusive access to open files and doesn't have atomic
        # rename, so just write into the final file.
        _write_pyc(state, co, source_stat, pyc)
    else:
        # When not on windows, assume rename is atomic. Dump the code object
        # into a file specific to this process and atomically replace it.
        proc_pyc = pyc + "." + str(os.getpid())
        if _write_pyc(state, co, source_stat, proc_pyc):
            os.rename(proc_pyc, pyc)


def _read_pyc(source, pyc, trace=lambda x: None):
    """Possibly read a pytest pyc containing rewritten code.

    Return rewritten code if successful or None if not.
    """
    import struct
    try:
        fp = open(pyc, "rb")
    except IOError:
        return None
    with fp:
        try:
            mtime = int(source.mtime())
            size = source.size()
            data = fp.read(12)
        except EnvironmentError as e:
            trace('_read_pyc(%s): EnvironmentError %s' % (source, e))
            return None
        # Check for invalid or out of date pyc file.
        if (len(data) != 12 or data[:4] != imp.get_magic() or
                struct.unpack("<ll", data[4:]) != (mtime, size)):
            trace('_read_pyc(%s): invalid or out of date pyc' % source)
            return None
        try:
            co = marshal.load(fp)
        except Exception as e:
            trace('_read_pyc(%s): marshal.load error %s' % (source, e))
            return None
        if not isinstance(co, types.CodeType):
            trace('_read_pyc(%s): not a code object' % source)
            return None
        return co


def _saferepr(obj):
    """Get a safe repr of an object for assertion error messages.

    The assertion formatting (util.format_explanation()) requires
    newlines to be escaped since they are a special character for it.
    Normally assertion.util.format_explanation() does this but for a
    custom repr it is possible to contain one of the special escape
    sequences, especially '\n{' and '\n}' are likely to be present in
    JSON reprs.

    """
    return repr(obj).replace('\n', '\\n')


def _format_assertmsg(obj):
    """Format the custom assertion message given.

    For strings this simply replaces newlines with '\n~' so that
    util.format_explanation() will preserve them instead of escaping
    newlines.  For other objects py.io.saferepr() is used first.

    """
    return obj.replace("\n", "\n~").replace("%", "%%")


def _should_repr_global_name(obj):
    return not hasattr(obj, "__name__") and not callable(obj)


def _format_boolop(explanations, is_or):
    explanation = "(" + (is_or and " or " or " and ").join(explanations) + ")"
    return explanation.replace('%', '%%')


def _call_reprcompare(ops, results, expls, each_obj):
    for i, res, expl in zip(range(len(ops)), results, expls):
        try:
            done = not res
        except Exception:
            done = True
        if done:
            break
    custom = callbinrepr(ops[i], each_obj[i], each_obj[i + 1])
    if custom is not None:
        return custom
    return expl


unary_map = {
    ast.Not: "not %s",
    ast.Invert: "~%s",
    ast.USub: "-%s",
    ast.UAdd: "+%s"
}

binop_map = {
    ast.BitOr: "|",
    ast.BitXor: "^",
    ast.BitAnd: "&",
    ast.LShift: "<<",
    ast.RShift: ">>",
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.FloorDiv: "//",
    ast.Mod: "%%",  # escaped for string formatting
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Pow: "**",
    ast.Is: "is",
    ast.IsNot: "is not",
    ast.In: "in",
    ast.NotIn: "not in"
}
# Python 3.5+ compatibility
try:
    binop_map[ast.MatMult] = "@"
except AttributeError:
    pass

# Python 3.4+ compatibility
if hasattr(ast, "NameConstant"):
    _NameConstant = ast.NameConstant
else:
    def _NameConstant(c):
        return ast.Name(str(c), ast.Load())


def set_location(node, lineno, col_offset):
    """Set node location information recursively."""
    def _fix(node, lineno, col_offset):
        if "lineno" in node._attributes:
            node.lineno = lineno
        if "col_offset" in node._attributes:
            node.col_offset = col_offset
        for child in ast.iter_child_nodes(node):
            _fix(child, lineno, col_offset)
    _fix(node, lineno, col_offset)
    return node


class AssertionRewriter(ast.NodeVisitor):
    """Assertion rewriting implementation.

    The main entrypoint is to call .run() with an ast.Module instance,
    this will then find all the assert statements and rewrite them to
    provide intermediate values and a detailed assertion error.  See
    http://pybites.blogspot.be/2011/07/behind-scenes-of-pytests-new-assertion.html
    for an overview of how this works.

    The entry point here is .run() which will iterate over all the
    statements in an ast.Module and for each ast.Assert statement it
    finds call .visit() with it.  Then .visit_Assert() takes over and
    is responsible for creating new ast statements to replace the
    original assert statement: it rewrites the test of an assertion
    to provide intermediate values and replace it with an if statement
    which raises an assertion error with a detailed explanation in
    case the expression is false.

    For this .visit_Assert() uses the visitor pattern to visit all the
    AST nodes of the ast.Assert.test field, each visit call returning
    an AST node and the corresponding explanation string.  During this
    state is kept in several instance attributes:

    :statements: All the AST statements which will replace the assert
       statement.

    :variables: This is populated by .variable() with each variable
       used by the statements so that they can all be set to None at
       the end of the statements.

    :variable_counter: Counter to create new unique variables needed
       by statements.  Variables are created using .variable() and
       have the form of "@py_assert0".

    :on_failure: The AST statements which will be executed if the
       assertion test fails.  This is the code which will construct
       the failure message and raises the AssertionError.

    :explanation_specifiers: A dict filled by .explanation_param()
       with %-formatting placeholders and their corresponding
       expressions to use in the building of an assertion message.
       This is used by .pop_format_context() to build a message.

    :stack: A stack of the explanation_specifiers dicts maintained by
       .push_format_context() and .pop_format_context() which allows
       to build another %-formatted string while already building one.

    This state is reset on every new assert statement visited and used
    by the other visitors.

    """

    def __init__(self, module_path):
        super(AssertionRewriter, self).__init__()
        self.module_path = module_path

    def run(self, mod):
        """Find all assert statements in *mod* and rewrite them."""
        if not mod.body:
            # Nothing to do.
            return
        # Insert some special imports at the top of the module but after any
        # docstrings and __future__ imports.
        if sys.version_info[0] >= 3:
            builtin_name = 'builtins'
        else:
            builtin_name = '__builtin__'
        aliases = [ast.alias(builtin_name, "@py_builtins"),
                   ast.alias("ast_rewrite", "@pytest_ar")]
        doc = getattr(mod, "docstring", None)
        expect_docstring = doc is None
        if doc is not None and self.is_rewrite_disabled(doc):
            return
        pos = 0
        lineno = 1
        for item in mod.body:
            if (expect_docstring and isinstance(item, ast.Expr) and
                    isinstance(item.value, ast.Str)):
                doc = item.value.s
                if self.is_rewrite_disabled(doc):
                    return
                expect_docstring = False
            elif (not isinstance(item, ast.ImportFrom) or item.level > 0 or
                  item.module != "__future__"):
                lineno = item.lineno
                break
            pos += 1
        else:
            lineno = item.lineno
        imports = [ast.Import([alias], lineno=lineno, col_offset=0)
                   for alias in aliases]
        mod.body[pos:pos] = imports
        # Collect asserts.
        nodes = [mod]
        while nodes:
            node = nodes.pop()
            for name, field in ast.iter_fields(node):
                if isinstance(field, list):
                    new = []
                    for i, child in enumerate(field):
                        if isinstance(child, ast.Assert):
                            # Transform assert.
                            new.extend(self.visit(child))
                        else:
                            new.append(child)
                            if isinstance(child, ast.AST):
                                nodes.append(child)
                    setattr(node, name, new)
                elif (isinstance(field, ast.AST) and
                      # Don't recurse into expressions as they can't contain
                      # asserts.
                      not isinstance(field, ast.expr)):
                    nodes.append(field)

    @staticmethod
    def is_rewrite_disabled(docstring):
        return "PYTEST_DONT_REWRITE" in docstring

    def variable(self):
        """Get a new variable."""
        # Use a character invalid in python identifiers to avoid clashing.
        name = "@py_assert" + str(next(self.variable_counter))
        self.variables.append(name)
        return name

    def assign(self, expr):
        """Give *expr* a name."""
        name = self.variable()
        self.statements.append(ast.Assign([ast.Name(name, ast.Store())], expr))
        return ast.Name(name, ast.Load())

    def display(self, expr):
        """Call py.io.saferepr on the expression."""
        return self.helper("saferepr", expr)

    def helper(self, name, *args):
        """Call a helper in this module."""
        py_name = ast.Name("@pytest_ar", ast.Load())
        attr = ast.Attribute(py_name, "_" + name, ast.Load())
        return ast_Call(attr, list(args), [])

    def builtin(self, name):
        """Return the builtin called *name*."""
        builtin_name = ast.Name("@py_builtins", ast.Load())
        return ast.Attribute(builtin_name, name, ast.Load())

    def explanation_param(self, expr):
        """Return a new named %-formatting placeholder for expr.

        This creates a %-formatting placeholder for expr in the
        current formatting context, e.g. ``%(py0)s``.  The placeholder
        and expr are placed in the current format context so that it
        can be used on the next call to .pop_format_context().

        """
        specifier = "py" + str(next(self.variable_counter))
        self.explanation_specifiers[specifier] = expr
        return "%(" + specifier + ")s"

    def push_format_context(self):
        """Create a new formatting context.

        The format context is used for when an explanation wants to
        have a variable value formatted in the assertion message.  In
        this case the value required can be added using
        .explanation_param().  Finally .pop_format_context() is used
        to format a string of %-formatted values as added by
        .explanation_param().

        """
        self.explanation_specifiers = {}
        self.stack.append(self.explanation_specifiers)

    def pop_format_context(self, expl_expr):
        """Format the %-formatted string with current format context.

        The expl_expr should be an ast.Str instance constructed from
        the %-placeholders created by .explanation_param().  This will
        add the required code to format said string to .on_failure and
        return the ast.Name instance of the formatted string.

        """
        current = self.stack.pop()
        if self.stack:
            self.explanation_specifiers = self.stack[-1]
        keys = [ast.Str(key) for key in current.keys()]
        format_dict = ast.Dict(keys, list(current.values()))
        form = ast.BinOp(expl_expr, ast.Mod(), format_dict)
        name = "@py_format" + str(next(self.variable_counter))
        self.on_failure.append(ast.Assign([ast.Name(name, ast.Store())], form))
        return ast.Name(name, ast.Load())

    def generic_visit(self, node):
        """Handle expressions we don't have custom code for."""
        assert isinstance(node, ast.expr)
        res = self.assign(node)
        return res, self.explanation_param(self.display(res))

    def visit_Assert(self, assert_):
        """Return the AST statements to replace the ast.Assert instance.

        This rewrites the test of an assertion to provide
        intermediate values and replace it with an if statement which
        raises an assertion error with a detailed explanation in case
        the expression is false.

        """
        self.statements = []
        self.variables = []
        self.variable_counter = itertools.count()
        self.stack = []
        self.on_failure = []
        self.push_format_context()
        # Rewrite assert into a bunch of statements.
        top_condition, explanation = self.visit(assert_.test)
        # Create failure message.
        body = self.on_failure
        negation = ast.UnaryOp(ast.Not(), top_condition)
        self.statements.append(ast.If(negation, body, []))
        if assert_.msg:
            assertmsg = self.helper('format_assertmsg', assert_.msg)
            explanation = "\n>assert " + explanation
        else:
            assertmsg = ast.Str("")
            explanation = "assert " + explanation
        template = ast.BinOp(assertmsg, ast.Add(), ast.Str(explanation))
        msg = self.pop_format_context(template)
        fmt = self.helper("format_explanation", msg)
        err_name = ast.Name("AssertionError", ast.Load())
        exc = ast_Call(err_name, [fmt], [])
        if sys.version_info[0] >= 3:
            raise_ = ast.Raise(exc, None)
        else:
            raise_ = ast.Raise(exc, None, None)
        body.append(raise_)
        # Clear temporary variables by setting them to None.
        if self.variables:
            variables = [ast.Name(name, ast.Store())
                         for name in self.variables]
            clear = ast.Assign(variables, _NameConstant(None))
            self.statements.append(clear)
        # Fix line numbers.
        for stmt in self.statements:
            set_location(stmt, assert_.lineno, assert_.col_offset)
        return self.statements

    def visit_Name(self, name):
        # Display the repr of the name if it's a local variable or
        # _should_repr_global_name() thinks it's acceptable.
        locs = ast_Call(self.builtin("locals"), [], [])
        inlocs = ast.Compare(ast.Str(name.id), [ast.In()], [locs])
        dorepr = self.helper("should_repr_global_name", name)
        test = ast.BoolOp(ast.Or(), [inlocs, dorepr])
        expr = ast.IfExp(test, self.display(name), ast.Str(name.id))
        return name, self.explanation_param(expr)

    def visit_BoolOp(self, boolop):
        res_var = self.variable()
        expl_list = self.assign(ast.List([], ast.Load()))
        app = ast.Attribute(expl_list, "append", ast.Load())
        is_or = int(isinstance(boolop.op, ast.Or))
        body = save = self.statements
        fail_save = self.on_failure
        levels = len(boolop.values) - 1
        self.push_format_context()
        # Process each operand, short-circuting if needed.
        for i, v in enumerate(boolop.values):
            if i:
                fail_inner = []
                # cond is set in a prior loop iteration below
                self.on_failure.append(ast.If(cond, fail_inner, []))  # noqa
                self.on_failure = fail_inner
            self.push_format_context()
            res, expl = self.visit(v)
            body.append(ast.Assign([ast.Name(res_var, ast.Store())], res))
            expl_format = self.pop_format_context(ast.Str(expl))
            call = ast_Call(app, [expl_format], [])
            self.on_failure.append(ast.Expr(call))
            if i < levels:
                cond = res
                if is_or:
                    cond = ast.UnaryOp(ast.Not(), cond)
                inner = []
                self.statements.append(ast.If(cond, inner, []))
                self.statements = body = inner
        self.statements = save
        self.on_failure = fail_save
        expl_template = self.helper("format_boolop", expl_list, ast.Num(is_or))
        expl = self.pop_format_context(expl_template)
        return ast.Name(res_var, ast.Load()), self.explanation_param(expl)

    def visit_UnaryOp(self, unary):
        pattern = unary_map[unary.op.__class__]
        operand_res, operand_expl = self.visit(unary.operand)
        res = self.assign(ast.UnaryOp(unary.op, operand_res))
        return res, pattern % (operand_expl,)

    def visit_BinOp(self, binop):
        symbol = binop_map[binop.op.__class__]
        left_expr, left_expl = self.visit(binop.left)
        right_expr, right_expl = self.visit(binop.right)
        explanation = "(%s %s %s)" % (left_expl, symbol, right_expl)
        res = self.assign(ast.BinOp(left_expr, binop.op, right_expr))
        return res, explanation

    def visit_Call_35(self, call):
        """
        visit `ast.Call` nodes on Python3.5 and after
        """
        new_func, func_expl = self.visit(call.func)
        arg_expls = []
        new_args = []
        new_kwargs = []
        for arg in call.args:
            res, expl = self.visit(arg)
            arg_expls.append(expl)
            new_args.append(res)
        for keyword in call.keywords:
            res, expl = self.visit(keyword.value)
            new_kwargs.append(ast.keyword(keyword.arg, res))
            if keyword.arg:
                arg_expls.append(keyword.arg + "=" + expl)
            else:  # **args have `arg` keywords with an .arg of None
                arg_expls.append("**" + expl)

        expl = "%s(%s)" % (func_expl, ', '.join(arg_expls))
        new_call = ast.Call(new_func, new_args, new_kwargs)
        res = self.assign(new_call)
        res_expl = self.explanation_param(self.display(res))
        outer_expl = "%s\n{%s = %s\n}" % (res_expl, res_expl, expl)
        return res, outer_expl

    def visit_Starred(self, starred):
        # From Python 3.5, a Starred node can appear in a function call
        res, expl = self.visit(starred.value)
        return starred, '*' + expl

    def visit_Call_legacy(self, call):
        """
        visit `ast.Call nodes on 3.4 and below`
        """
        new_func, func_expl = self.visit(call.func)
        arg_expls = []
        new_args = []
        new_kwargs = []
        new_star = new_kwarg = None
        for arg in call.args:
            res, expl = self.visit(arg)
            new_args.append(res)
            arg_expls.append(expl)
        for keyword in call.keywords:
            res, expl = self.visit(keyword.value)
            new_kwargs.append(ast.keyword(keyword.arg, res))
            arg_expls.append(keyword.arg + "=" + expl)
        if call.starargs:
            new_star, expl = self.visit(call.starargs)
            arg_expls.append("*" + expl)
        if call.kwargs:
            new_kwarg, expl = self.visit(call.kwargs)
            arg_expls.append("**" + expl)
        expl = "%s(%s)" % (func_expl, ', '.join(arg_expls))
        new_call = ast.Call(new_func, new_args, new_kwargs,
                            new_star, new_kwarg)
        res = self.assign(new_call)
        res_expl = self.explanation_param(self.display(res))
        outer_expl = "%s\n{%s = %s\n}" % (res_expl, res_expl, expl)
        return res, outer_expl

    # ast.Call signature changed on 3.5,
    # conditionally change  which methods is named
    # visit_Call depending on Python version
    if sys.version_info >= (3, 5):
        visit_Call = visit_Call_35
    else:
        visit_Call = visit_Call_legacy

    def visit_Attribute(self, attr):
        if not isinstance(attr.ctx, ast.Load):
            return self.generic_visit(attr)
        value, value_expl = self.visit(attr.value)
        res = self.assign(ast.Attribute(value, attr.attr, ast.Load()))
        res_expl = self.explanation_param(self.display(res))
        pat = "%s\n{%s = %s.%s\n}"
        expl = pat % (res_expl, res_expl, value_expl, attr.attr)
        return res, expl

    def visit_Compare(self, comp):
        self.push_format_context()
        left_res, left_expl = self.visit(comp.left)
        if isinstance(comp.left, (ast.Compare, ast.BoolOp)):
            left_expl = "({0})".format(left_expl)
        res_variables = [self.variable() for i in range(len(comp.ops))]
        load_names = [ast.Name(v, ast.Load()) for v in res_variables]
        store_names = [ast.Name(v, ast.Store()) for v in res_variables]
        it = zip(range(len(comp.ops)), comp.ops, comp.comparators)
        expls = []
        syms = []
        results = [left_res]
        for i, op, next_operand in it:
            next_res, next_expl = self.visit(next_operand)
            if isinstance(next_operand, (ast.Compare, ast.BoolOp)):
                next_expl = "({0})".format(next_expl)
            results.append(next_res)
            sym = binop_map[op.__class__]
            syms.append(ast.Str(sym))
            expl = "%s %s %s" % (left_expl, sym, next_expl)
            expls.append(ast.Str(expl))
            res_expr = ast.Compare(left_res, [op], [next_res])
            self.statements.append(ast.Assign([store_names[i]], res_expr))
            left_res, left_expl = next_res, next_expl
        # Use pytest.assertion.util._reprcompare if that's available.
        expl_call = self.helper("call_reprcompare",
                                ast.Tuple(syms, ast.Load()),
                                ast.Tuple(load_names, ast.Load()),
                                ast.Tuple(expls, ast.Load()),
                                ast.Tuple(results, ast.Load()))
        if len(comp.ops) > 1:
            res = ast.BoolOp(ast.And(), load_names)
        else:
            res = load_names[0]
        return res, self.explanation_param(self.pop_format_context(expl_call))
