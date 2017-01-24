from pypy.interpreter.astcompiler import ast, consts, misc
from pypy.interpreter.astcompiler import asthelpers # Side effects
from pypy.interpreter.astcompiler import fstring
from pypy.interpreter import error
from pypy.interpreter.pyparser.pygram import syms, tokens
from pypy.interpreter.pyparser.error import SyntaxError
from rpython.rlib.objectmodel import always_inline, we_are_translated


def ast_from_node(space, node, compile_info, recursive_parser=None):
    """Turn a parse tree, node, to AST."""
    ast = ASTBuilder(space, node, compile_info, recursive_parser).build_ast()
    #
    # When we are not translated, we send this ast to validate_ast.
    # The goal is to check that validate_ast doesn't crash on valid
    # asts, at least.
    if not we_are_translated():
        from pypy.interpreter.astcompiler import validate
        validate.validate_ast(space, ast)
    return ast


augassign_operator_map = {
    '+='  : ast.Add,
    '-='  : ast.Sub,
    '/='  : ast.Div,
    '//=' : ast.FloorDiv,
    '%='  : ast.Mod,
    '@='  : ast.MatMult,
    '<<='  : ast.LShift,
    '>>='  : ast.RShift,
    '&='  : ast.BitAnd,
    '|='  : ast.BitOr,
    '^='  : ast.BitXor,
    '*='  : ast.Mult,
    '**=' : ast.Pow
}

operator_map = misc.dict_to_switch({
    tokens.VBAR : ast.BitOr,
    tokens.CIRCUMFLEX : ast.BitXor,
    tokens.AMPER : ast.BitAnd,
    tokens.LEFTSHIFT : ast.LShift,
    tokens.RIGHTSHIFT : ast.RShift,
    tokens.PLUS : ast.Add,
    tokens.MINUS : ast.Sub,
    tokens.STAR : ast.Mult,
    tokens.SLASH : ast.Div,
    tokens.DOUBLESLASH : ast.FloorDiv,
    tokens.PERCENT : ast.Mod,
    tokens.AT : ast.MatMult
})


class ASTBuilder(object):

    def __init__(self, space, n, compile_info, recursive_parser=None):
        self.space = space
        self.compile_info = compile_info
        self.root_node = n
        self.recursive_parser = recursive_parser

    def build_ast(self):
        """Convert an top level parse tree node into an AST mod."""
        n = self.root_node
        if n.type == syms.file_input:
            stmts = []
            for i in range(n.num_children() - 1):
                stmt = n.get_child(i)
                if stmt.type == tokens.NEWLINE:
                    continue
                sub_stmts_count = self.number_of_statements(stmt)
                if sub_stmts_count == 1:
                    stmts.append(self.handle_stmt(stmt))
                else:
                    stmt = stmt.get_child(0)
                    for j in range(sub_stmts_count):
                        small_stmt = stmt.get_child(j * 2)
                        stmts.append(self.handle_stmt(small_stmt))
            return ast.Module(stmts)
        elif n.type == syms.eval_input:
            body = self.handle_testlist(n.get_child(0))
            return ast.Expression(body)
        elif n.type == syms.single_input:
            first_child = n.get_child(0)
            if first_child.type == tokens.NEWLINE:
                # An empty line.
                return ast.Interactive([])
            else:
                num_stmts = self.number_of_statements(first_child)
                if num_stmts == 1:
                    stmts = [self.handle_stmt(first_child)]
                else:
                    stmts = []
                    for i in range(0, first_child.num_children(), 2):
                        stmt = first_child.get_child(i)
                        if stmt.type == tokens.NEWLINE:
                            break
                        stmts.append(self.handle_stmt(stmt))
                return ast.Interactive(stmts)
        else:
            raise AssertionError("unknown root node")

    def number_of_statements(self, n):
        """Compute the number of AST statements contained in a node."""
        stmt_type = n.type
        if stmt_type == syms.compound_stmt:
            return 1
        elif stmt_type == syms.stmt:
            return self.number_of_statements(n.get_child(0))
        elif stmt_type == syms.simple_stmt:
            # Divide to remove semi-colons.
            return n.num_children() // 2
        else:
            raise AssertionError("non-statement node")

    def error(self, msg, n):
        """Raise a SyntaxError with the lineno and column set to n's."""
        raise SyntaxError(msg, n.get_lineno(), n.get_column(),
                          filename=self.compile_info.filename)

    def error_ast(self, msg, ast_node):
        raise SyntaxError(msg, ast_node.lineno, ast_node.col_offset,
                          filename=self.compile_info.filename)

    def check_forbidden_name(self, name, node):
        try:
            misc.check_forbidden_name(name)
        except misc.ForbiddenNameAssignment as e:
            self.error("cannot assign to %s" % (e.name,), node)

    def new_identifier(self, name):
        return misc.new_identifier(self.space, name)

    def set_context(self, expr, ctx):
        """Set the context of an expression to Store or Del if possible."""
        try:
            expr.set_context(ctx)
        except ast.UnacceptableExpressionContext as e:
            self.error_ast(e.msg, e.node)
        except misc.ForbiddenNameAssignment as e:
            self.error_ast("cannot assign to %s" % (e.name,), e.node)

    def handle_del_stmt(self, del_node):
        targets = self.handle_exprlist(del_node.get_child(1), ast.Del)
        return ast.Delete(targets, del_node.get_lineno(), del_node.get_column())

    def handle_flow_stmt(self, flow_node):
        first_child = flow_node.get_child(0)
        first_child_type = first_child.type
        if first_child_type == syms.break_stmt:
            return ast.Break(flow_node.get_lineno(), flow_node.get_column())
        elif first_child_type == syms.continue_stmt:
            return ast.Continue(flow_node.get_lineno(), flow_node.get_column())
        elif first_child_type == syms.yield_stmt:
            yield_expr = self.handle_expr(first_child.get_child(0))
            return ast.Expr(yield_expr, flow_node.get_lineno(), flow_node.get_column())
        elif first_child_type == syms.return_stmt:
            if first_child.num_children() == 1:
                values = None
            else:
                values = self.handle_testlist(first_child.get_child(1))
            return ast.Return(values, flow_node.get_lineno(), flow_node.get_column())
        elif first_child_type == syms.raise_stmt:
            exc = None
            cause = None
            child_count = first_child.num_children()
            if child_count >= 2:
                exc = self.handle_expr(first_child.get_child(1))
            if child_count >= 4:
                cause = self.handle_expr(first_child.get_child(3))
            return ast.Raise(exc, cause, flow_node.get_lineno(), flow_node.get_column())
        else:
            raise AssertionError("unknown flow statement")

    def alias_for_import_name(self, import_name, store=True):
        while True:
            import_name_type = import_name.type
            if import_name_type == syms.import_as_name:
                name = self.new_identifier(import_name.get_child(0).get_value())
                if import_name.num_children() == 3:
                    as_name = self.new_identifier(
                        import_name.get_child(2).get_value())
                    self.check_forbidden_name(as_name, import_name.get_child(2))
                else:
                    as_name = None
                    self.check_forbidden_name(name, import_name.get_child(0))
                return ast.alias(name, as_name)
            elif import_name_type == syms.dotted_as_name:
                if import_name.num_children() == 1:
                    import_name = import_name.get_child(0)
                    continue
                alias = self.alias_for_import_name(import_name.get_child(0),
                                                   store=False)
                asname_node = import_name.get_child(2)
                alias.asname = self.new_identifier(asname_node.get_value())
                self.check_forbidden_name(alias.asname, asname_node)
                return alias
            elif import_name_type == syms.dotted_name:
                if import_name.num_children() == 1:
                    name = self.new_identifier(import_name.get_child(0).get_value())
                    if store:
                        self.check_forbidden_name(name, import_name.get_child(0))
                    return ast.alias(name, None)
                name_parts = [import_name.get_child(i).get_value()
                              for i in range(0, import_name.num_children(), 2)]
                name = ".".join(name_parts)
                return ast.alias(name, None)
            elif import_name_type == tokens.STAR:
                return ast.alias("*", None)
            else:
                raise AssertionError("unknown import name")

    def handle_import_stmt(self, import_node):
        import_node = import_node.get_child(0)
        if import_node.type == syms.import_name:
            dotted_as_names = import_node.get_child(1)
            aliases = [self.alias_for_import_name(dotted_as_names.get_child(i))
                       for i in range(0, dotted_as_names.num_children(), 2)]
            return ast.Import(aliases, import_node.get_lineno(), import_node.get_column())
        elif import_node.type == syms.import_from:
            child_count = import_node.num_children()
            module = None
            modname = None
            i = 1
            dot_count = 0
            while i < child_count:
                child = import_node.get_child(i)
                child_type = child.type
                if child_type == syms.dotted_name:
                    module = self.alias_for_import_name(child, False)
                    i += 1
                    break
                elif child_type == tokens.ELLIPSIS:
                    # Special case for tokenization.
                    dot_count += 2
                elif child_type != tokens.DOT:
                    break
                i += 1
                dot_count += 1
            i += 1
            after_import_type = import_node.get_child(i).type
            star_import = False
            if after_import_type == tokens.STAR:
                names_node = import_node.get_child(i)
                star_import = True
            elif after_import_type == tokens.LPAR:
                names_node = import_node.get_child(i + 1)
            elif after_import_type == syms.import_as_names:
                names_node = import_node.get_child(i)
                if names_node.num_children() % 2 == 0:
                    self.error("trailing comma is only allowed with "
                               "surronding parenthesis", names_node)
            else:
                raise AssertionError("unknown import node")
            if star_import:
                aliases = [self.alias_for_import_name(names_node)]
            else:
                aliases = [self.alias_for_import_name(names_node.get_child(i))
                           for i in range(0, names_node.num_children(), 2)]
            if module is not None:
                modname = module.name
            return ast.ImportFrom(modname, aliases, dot_count,
                                  import_node.get_lineno(), import_node.get_column())
        else:
            raise AssertionError("unknown import node")

    def handle_global_stmt(self, global_node):
        names = [self.new_identifier(global_node.get_child(i).get_value())
                 for i in range(1, global_node.num_children(), 2)]
        return ast.Global(names, global_node.get_lineno(), global_node.get_column())

    def handle_nonlocal_stmt(self, nonlocal_node):
        names = [self.new_identifier(nonlocal_node.get_child(i).get_value())
                 for i in range(1, nonlocal_node.num_children(), 2)]
        return ast.Nonlocal(names, nonlocal_node.get_lineno(), nonlocal_node.get_column())

    def handle_assert_stmt(self, assert_node):
        expr = self.handle_expr(assert_node.get_child(1))
        msg = None
        if assert_node.num_children() == 4:
            msg = self.handle_expr(assert_node.get_child(3))
        return ast.Assert(expr, msg, assert_node.get_lineno(), assert_node.get_column())

    def handle_suite(self, suite_node):
        first_child = suite_node.get_child(0)
        if first_child.type == syms.simple_stmt:
            end = first_child.num_children() - 1
            if first_child.get_child(end - 1).type == tokens.SEMI:
                end -= 1
            stmts = [self.handle_stmt(first_child.get_child(i))
                     for i in range(0, end, 2)]
        else:
            stmts = []
            for i in range(2, suite_node.num_children() - 1):
                stmt = suite_node.get_child(i)
                stmt_count = self.number_of_statements(stmt)
                if stmt_count == 1:
                    stmts.append(self.handle_stmt(stmt))
                else:
                    simple_stmt = stmt.get_child(0)
                    for j in range(0, simple_stmt.num_children(), 2):
                        stmt = simple_stmt.get_child(j)
                        if not stmt.num_children():
                            break
                        stmts.append(self.handle_stmt(stmt))
        return stmts

    def handle_if_stmt(self, if_node):
        child_count = if_node.num_children()
        if child_count == 4:
            test = self.handle_expr(if_node.get_child(1))
            suite = self.handle_suite(if_node.get_child(3))
            return ast.If(test, suite, None, if_node.get_lineno(), if_node.get_column())
        otherwise_string = if_node.get_child(4).get_value()
        if otherwise_string == "else":
            test = self.handle_expr(if_node.get_child(1))
            suite = self.handle_suite(if_node.get_child(3))
            else_suite = self.handle_suite(if_node.get_child(6))
            return ast.If(test, suite, else_suite, if_node.get_lineno(),
                          if_node.get_column())
        elif otherwise_string == "elif":
            elif_count = child_count - 4
            after_elif = if_node.get_child(elif_count + 1)
            if after_elif.type == tokens.NAME and \
                    after_elif.get_value() == "else":
                has_else = True
                elif_count -= 3
            else:
                has_else = False
            elif_count /= 4
            if has_else:
                last_elif = if_node.get_child(-6)
                last_elif_test = self.handle_expr(last_elif)
                elif_body = self.handle_suite(if_node.get_child(-4))
                else_body = self.handle_suite(if_node.get_child(-1))
                otherwise = [ast.If(last_elif_test, elif_body, else_body,
                                    last_elif.get_lineno(), last_elif.get_column())]
                elif_count -= 1
            else:
                otherwise = None
            for i in range(elif_count):
                offset = 5 + (elif_count - i - 1) * 4
                elif_test_node = if_node.get_child(offset)
                elif_test = self.handle_expr(elif_test_node)
                elif_body = self.handle_suite(if_node.get_child(offset + 2))
                new_if = ast.If(elif_test, elif_body, otherwise,
                                elif_test_node.get_lineno(), elif_test_node.get_column())
                otherwise = [new_if]
            expr = self.handle_expr(if_node.get_child(1))
            body = self.handle_suite(if_node.get_child(3))
            return ast.If(expr, body, otherwise, if_node.get_lineno(), if_node.get_column())
        else:
            raise AssertionError("unknown if statement configuration")

    def handle_while_stmt(self, while_node):
        loop_test = self.handle_expr(while_node.get_child(1))
        body = self.handle_suite(while_node.get_child(3))
        if while_node.num_children() == 7:
            otherwise = self.handle_suite(while_node.get_child(6))
        else:
            otherwise = None
        return ast.While(loop_test, body, otherwise, while_node.get_lineno(),
                         while_node.get_column())

    def handle_for_stmt(self, for_node, is_async):
        target_node = for_node.get_child(1)
        target_as_exprlist = self.handle_exprlist(target_node, ast.Store)
        if target_node.num_children() == 1:
            target = target_as_exprlist[0]
        else:
            target = ast.Tuple(target_as_exprlist, ast.Store,
                               target_node.get_lineno(), target_node.get_column())
        expr = self.handle_testlist(for_node.get_child(3))
        body = self.handle_suite(for_node.get_child(5))
        if for_node.num_children() == 9:
            otherwise = self.handle_suite(for_node.get_child(8))
        else:
            otherwise = None
        if is_async:
            return ast.AsyncFor(target, expr, body, otherwise, for_node.get_lineno(),
                                for_node.get_column())
        else:
            return ast.For(target, expr, body, otherwise, for_node.get_lineno(),
                           for_node.get_column())

    def handle_except_clause(self, exc, body):
        test = None
        name = None
        suite = self.handle_suite(body)
        child_count = exc.num_children()
        if child_count >= 2:
            test = self.handle_expr(exc.get_child(1))
        if child_count == 4:
            name_node = exc.get_child(3)
            name = self.new_identifier(name_node.get_value())
            self.check_forbidden_name(name, name_node)
        return ast.ExceptHandler(test, name, suite, exc.get_lineno(), exc.get_column())

    def handle_try_stmt(self, try_node):
        body = self.handle_suite(try_node.get_child(2))
        child_count = try_node.num_children()
        except_count = (child_count - 3 ) // 3
        otherwise = None
        finally_suite = None
        possible_extra_clause = try_node.get_child(-3)
        if possible_extra_clause.type == tokens.NAME:
            if possible_extra_clause.get_value() == "finally":
                if child_count >= 9 and \
                        try_node.get_child(-6).type == tokens.NAME:
                    otherwise = self.handle_suite(try_node.get_child(-4))
                    except_count -= 1
                finally_suite = self.handle_suite(try_node.get_child(-1))
                except_count -= 1
            else:
                otherwise = self.handle_suite(try_node.get_child(-1))
                except_count -= 1
        handlers = []
        if except_count:
            for i in range(except_count):
                base_offset = i * 3
                exc = try_node.get_child(3 + base_offset)
                except_body = try_node.get_child(5 + base_offset)
                handlers.append(self.handle_except_clause(exc, except_body))
        return ast.Try(body, handlers, otherwise, finally_suite,
                       try_node.get_lineno(), try_node.get_column())

    def handle_with_item(self, item_node):
        test = self.handle_expr(item_node.get_child(0))
        if item_node.num_children() == 3:
            target = self.handle_expr(item_node.get_child(2))
            self.set_context(target, ast.Store)
        else:
            target = None
        return ast.withitem(test, target)

    def handle_with_stmt(self, with_node, is_async):
        body = self.handle_suite(with_node.get_child(-1))
        items = [self.handle_with_item(with_node.get_child(i))
                 for i in range(1, with_node.num_children()-2, 2)]
        if is_async:
            return ast.AsyncWith(items, body, with_node.get_lineno(),
                                 with_node.get_column())
        else:
            return ast.With(items, body, with_node.get_lineno(),
                            with_node.get_column())

    def handle_classdef(self, classdef_node, decorators=None):
        name_node = classdef_node.get_child(1)
        name = self.new_identifier(name_node.get_value())
        self.check_forbidden_name(name, name_node)
        if classdef_node.num_children() == 4:
            # class NAME ':' suite
            body = self.handle_suite(classdef_node.get_child(3))
            return ast.ClassDef(name, None, None, body, decorators,
                                classdef_node.get_lineno(), classdef_node.get_column())
        if classdef_node.get_child(3).type == tokens.RPAR:
            # class NAME '(' ')' ':' suite
            body = self.handle_suite(classdef_node.get_child(5))
            return ast.ClassDef(name, None, None, body, decorators,
                                classdef_node.get_lineno(), classdef_node.get_column())

        # class NAME '(' arglist ')' ':' suite
        # build up a fake Call node so we can extract its pieces
        call_name = ast.Name(name, ast.Load, classdef_node.get_lineno(),
                             classdef_node.get_column())
        call = self.handle_call(classdef_node.get_child(3), call_name)
        body = self.handle_suite(classdef_node.get_child(6))
        return ast.ClassDef(
            name, call.args, call.keywords,
            body, decorators, classdef_node.get_lineno(), classdef_node.get_column())

    def handle_class_bases(self, bases_node):
        if bases_node.num_children() == 1:
            return [self.handle_expr(bases_node.get_child(0))]
        return self.get_expression_list(bases_node)

    def handle_funcdef_impl(self, funcdef_node, is_async, decorators=None):
        name_node = funcdef_node.get_child(1)
        name = self.new_identifier(name_node.get_value())
        self.check_forbidden_name(name, name_node)
        args = self.handle_arguments(funcdef_node.get_child(2))
        suite = 4
        returns = None
        if funcdef_node.get_child(3).type == tokens.RARROW:
            returns = self.handle_expr(funcdef_node.get_child(4))
            suite += 2
        body = self.handle_suite(funcdef_node.get_child(suite))
        if is_async:
            return ast.AsyncFunctionDef(name, args, body, decorators, returns,
                                        funcdef_node.get_lineno(), funcdef_node.get_column())
        else:
            return ast.FunctionDef(name, args, body, decorators, returns,
                                   funcdef_node.get_lineno(), funcdef_node.get_column())

    def handle_async_funcdef(self, node, decorators=None):
        return self.handle_funcdef_impl(node.get_child(1), 1, decorators)
    
    def handle_funcdef(self, node, decorators=None):
        return self.handle_funcdef_impl(node, 0, decorators)
    
    def handle_async_stmt(self, node):
        ch = node.get_child(1)
        if ch.type == syms.funcdef:
            return self.handle_funcdef_impl(ch, 1)
        elif ch.type == syms.with_stmt:
            return self.handle_with_stmt(ch, 1)
        elif ch.type == syms.for_stmt:
            return self.handle_for_stmt(ch, 1)
        else:
            raise AssertionError("invalid async statement")

    def handle_decorated(self, decorated_node):
        decorators = self.handle_decorators(decorated_node.get_child(0))
        definition = decorated_node.get_child(1)
        if definition.type == syms.funcdef:
            node = self.handle_funcdef(definition, decorators)
        elif definition.type == syms.classdef:
            node = self.handle_classdef(definition, decorators)
        elif definition.type == syms.async_funcdef:
            node = self.handle_async_funcdef(definition, decorators)
        else:
            raise AssertionError("unkown decorated")
        node.lineno = decorated_node.get_lineno()
        node.col_offset = decorated_node.get_column()
        return node

    def handle_decorators(self, decorators_node):
        return [self.handle_decorator(decorators_node.get_child(i))
                    for i in range(decorators_node.num_children())]

    def handle_decorator(self, decorator_node):
        dec_name = self.handle_dotted_name(decorator_node.get_child(1))
        if decorator_node.num_children() == 3:
            dec = dec_name
        elif decorator_node.num_children() == 5:
            dec = ast.Call(dec_name, None, None,
                           decorator_node.get_lineno(), decorator_node.get_column())
        else:
            dec = self.handle_call(decorator_node.get_child(3), dec_name)
        return dec

    def handle_dotted_name(self, dotted_name_node):
        base_value = self.new_identifier(dotted_name_node.get_child(0).get_value())
        name = ast.Name(base_value, ast.Load, dotted_name_node.get_lineno(),
                        dotted_name_node.get_column())
        for i in range(2, dotted_name_node.num_children(), 2):
            attr = dotted_name_node.get_child(i).get_value()
            attr = self.new_identifier(attr)
            name = ast.Attribute(name, attr, ast.Load, dotted_name_node.get_lineno(),
                                 dotted_name_node.get_column())
        return name

    def handle_arguments(self, arguments_node):
        # This function handles both typedargslist (function definition)
        # and varargslist (lambda definition).
        if arguments_node.type == syms.parameters:
            if arguments_node.num_children() == 2:
                return ast.arguments(None, None, None, None, None, None)
            arguments_node = arguments_node.get_child(1)
        i = 0
        child_count = arguments_node.num_children()
        n_pos = 0
        n_pos_def = 0
        n_kwdonly = 0
        # scan args
        while i < child_count:
            arg_type = arguments_node.get_child(i).type
            if arg_type == tokens.STAR:
                i += 1
                if i < child_count:
                    next_arg_type = arguments_node.get_child(i).type
                    if (next_arg_type == syms.tfpdef or
                        next_arg_type == syms.vfpdef):
                        i += 1
                break
            if arg_type == tokens.DOUBLESTAR:
                break
            if arg_type == syms.vfpdef or arg_type == syms.tfpdef:
                n_pos += 1
            if arg_type == tokens.EQUAL:
                n_pos_def += 1
            i += 1
        while i < child_count:
            arg_type = arguments_node.get_child(i).type
            if arg_type == tokens.DOUBLESTAR:
                break
            if arg_type == syms.vfpdef or arg_type == syms.tfpdef:
                n_kwdonly += 1
            i += 1
        pos = []
        posdefaults = []
        kwonly = [] if n_kwdonly else None
        kwdefaults = []
        kwarg = None
        vararg = None
        if n_pos + n_kwdonly > 255:
            self.error("more than 255 arguments", arguments_node)
        # process args
        i = 0
        have_default = False
        while i < child_count:
            arg = arguments_node.get_child(i)
            arg_type = arg.type
            if arg_type == syms.tfpdef or arg_type == syms.vfpdef:
                if i + 1 < child_count and \
                        arguments_node.get_child(i + 1).type == tokens.EQUAL:
                    default_node = arguments_node.get_child(i + 2)
                    posdefaults.append(self.handle_expr(default_node))
                    i += 2
                    have_default = True
                elif have_default:
                    msg = "non-default argument follows default argument"
                    self.error(msg, arguments_node)
                pos.append(self.handle_arg(arg))
                i += 2
            elif arg_type == tokens.STAR:
                if i + 1 >= child_count:
                    self.error("named arguments must follow bare *",
                               arguments_node)
                name_node = arguments_node.get_child(i + 1)
                keywordonly_args = []
                if name_node.type == tokens.COMMA:
                    i += 2
                    i = self.handle_keywordonly_args(arguments_node, i, kwonly,
                                                     kwdefaults)
                else:
                    vararg = self.handle_arg(name_node)
                    i += 3
                    if i < child_count:
                        next_arg_type = arguments_node.get_child(i).type
                        if (next_arg_type == syms.tfpdef or
                            next_arg_type == syms.vfpdef):
                            i = self.handle_keywordonly_args(arguments_node, i,
                                                             kwonly, kwdefaults)
            elif arg_type == tokens.DOUBLESTAR:
                name_node = arguments_node.get_child(i + 1)
                kwarg = self.handle_arg(name_node)
                i += 3
            else:
                raise AssertionError("unknown node in argument list")
        return ast.arguments(pos, vararg, kwonly, kwdefaults, kwarg,
                             posdefaults)

    def handle_keywordonly_args(self, arguments_node, i, kwonly, kwdefaults):
        if kwonly is None:
            self.error("named arguments must follows bare *",
                       arguments_node.get_child(i))
        child_count = arguments_node.num_children()
        while i < child_count:
            arg = arguments_node.get_child(i)
            arg_type = arg.type
            if arg_type == syms.vfpdef or arg_type == syms.tfpdef:
                if (i + 1 < child_count and
                    arguments_node.get_child(i + 1).type == tokens.EQUAL):
                    expr = self.handle_expr(arguments_node.get_child(i + 2))
                    kwdefaults.append(expr)
                    i += 2
                else:
                    kwdefaults.append(None)
                ann = None
                if arg.num_children() == 3:
                    ann = self.handle_expr(arg.get_child(2))
                name_node = arg.get_child(0)
                argname = name_node.get_value()
                argname = self.new_identifier(argname)
                self.check_forbidden_name(argname, name_node)
                kwonly.append(ast.arg(argname, ann, arg.get_lineno(),
                                                    arg.get_column()))
                i += 2
            elif arg_type == tokens.DOUBLESTAR:
                return i
        return i

    def handle_arg(self, arg_node):
        name_node = arg_node.get_child(0)
        name = self.new_identifier(name_node.get_value())
        self.check_forbidden_name(name, arg_node)
        ann = None
        if arg_node.num_children() == 3:
            ann = self.handle_expr(arg_node.get_child(2))
        return ast.arg(name, ann, arg_node.get_lineno(), arg_node.get_column())

    def handle_stmt(self, stmt):
        stmt_type = stmt.type
        if stmt_type == syms.stmt:
            stmt = stmt.get_child(0)
            stmt_type = stmt.type
        if stmt_type == syms.simple_stmt:
            stmt = stmt.get_child(0)
            stmt_type = stmt.type
        if stmt_type == syms.small_stmt:
            stmt = stmt.get_child(0)
            stmt_type = stmt.type
            if stmt_type == syms.expr_stmt:
                return self.handle_expr_stmt(stmt)
            elif stmt_type == syms.del_stmt:
                return self.handle_del_stmt(stmt)
            elif stmt_type == syms.pass_stmt:
                return ast.Pass(stmt.get_lineno(), stmt.get_column())
            elif stmt_type == syms.flow_stmt:
                return self.handle_flow_stmt(stmt)
            elif stmt_type == syms.import_stmt:
                return self.handle_import_stmt(stmt)
            elif stmt_type == syms.global_stmt:
                return self.handle_global_stmt(stmt)
            elif stmt_type == syms.nonlocal_stmt:
                return self.handle_nonlocal_stmt(stmt)
            elif stmt_type == syms.assert_stmt:
                return self.handle_assert_stmt(stmt)
            else:
                raise AssertionError("unhandled small statement")
        elif stmt_type == syms.compound_stmt:
            stmt = stmt.get_child(0)
            stmt_type = stmt.type
            if stmt_type == syms.if_stmt:
                return self.handle_if_stmt(stmt)
            elif stmt_type == syms.while_stmt:
                return self.handle_while_stmt(stmt)
            elif stmt_type == syms.for_stmt:
                return self.handle_for_stmt(stmt, 0)
            elif stmt_type == syms.try_stmt:
                return self.handle_try_stmt(stmt)
            elif stmt_type == syms.with_stmt:
                return self.handle_with_stmt(stmt, 0)
            elif stmt_type == syms.funcdef:
                return self.handle_funcdef(stmt)
            elif stmt_type == syms.classdef:
                return self.handle_classdef(stmt)
            elif stmt_type == syms.decorated:
                return self.handle_decorated(stmt)
            elif stmt_type == syms.async_stmt:
                return self.handle_async_stmt(stmt)
            else:
                raise AssertionError("unhandled compound statement")
        else:
            raise AssertionError("unknown statment type")

    def handle_expr_stmt(self, stmt):
        if stmt.num_children() == 1:
            expression = self.handle_testlist(stmt.get_child(0))
            return ast.Expr(expression, stmt.get_lineno(), stmt.get_column())
        elif stmt.get_child(1).type == syms.augassign:
            # Augmented assignment.
            target_child = stmt.get_child(0)
            target_expr = self.handle_testlist(target_child)
            self.set_context(target_expr, ast.Store)
            value_child = stmt.get_child(2)
            if value_child.type == syms.testlist:
                value_expr = self.handle_testlist(value_child)
            else:
                value_expr = self.handle_expr(value_child)
            op_str = stmt.get_child(1).get_child(0).get_value()
            operator = augassign_operator_map[op_str]
            return ast.AugAssign(target_expr, operator, value_expr,
                                 stmt.get_lineno(), stmt.get_column())
        else:
            # Normal assignment.
            targets = []
            for i in range(0, stmt.num_children() - 2, 2):
                target_node = stmt.get_child(i)
                if target_node.type == syms.yield_expr:
                    self.error("assignment to yield expression not possible",
                               target_node)
                target_expr = self.handle_testlist(target_node)
                self.set_context(target_expr, ast.Store)
                targets.append(target_expr)
            value_child = stmt.get_child(-1)
            if value_child.type == syms.testlist_star_expr:
                value_expr = self.handle_testlist(value_child)
            else:
                value_expr = self.handle_expr(value_child)
            return ast.Assign(targets, value_expr, stmt.get_lineno(), stmt.get_column())

    def get_expression_list(self, tests):
        return [self.handle_expr(tests.get_child(i))
                for i in range(0, tests.num_children(), 2)]

    def handle_testlist(self, tests):
        if tests.num_children() == 1:
            return self.handle_expr(tests.get_child(0))
        else:
            elts = self.get_expression_list(tests)
            return ast.Tuple(elts, ast.Load, tests.get_lineno(), tests.get_column())

    def handle_expr(self, expr_node):
        # Loop until we return something.
        while True:
            expr_node_type = expr_node.type
            if expr_node_type == syms.test or expr_node_type == syms.test_nocond:
                first_child = expr_node.get_child(0)
                if first_child.type in (syms.lambdef, syms.lambdef_nocond):
                    return self.handle_lambdef(first_child)
                elif expr_node.num_children() > 1:
                    return self.handle_ifexp(expr_node)
                else:
                    expr_node = first_child
            elif expr_node_type == syms.or_test or \
                    expr_node_type == syms.and_test:
                if expr_node.num_children() == 1:
                    expr_node = expr_node.get_child(0)
                    continue
                seq = [self.handle_expr(expr_node.get_child(i))
                       for i in range(0, expr_node.num_children(), 2)]
                if expr_node_type == syms.or_test:
                    op = ast.Or
                else:
                    op = ast.And
                return ast.BoolOp(op, seq, expr_node.get_lineno(), expr_node.get_column())
            elif expr_node_type == syms.not_test:
                if expr_node.num_children() == 1:
                    expr_node = expr_node.get_child(0)
                    continue
                expr = self.handle_expr(expr_node.get_child(1))
                return ast.UnaryOp(ast.Not, expr, expr_node.get_lineno(),
                                   expr_node.get_column())
            elif expr_node_type == syms.comparison:
                if expr_node.num_children() == 1:
                    expr_node = expr_node.get_child(0)
                    continue
                operators = []
                operands = []
                expr = self.handle_expr(expr_node.get_child(0))
                for i in range(1, expr_node.num_children(), 2):
                    operators.append(self.handle_comp_op(expr_node.get_child(i)))
                    operands.append(self.handle_expr(expr_node.get_child(i + 1)))
                return ast.Compare(expr, operators, operands, expr_node.get_lineno(),
                                   expr_node.get_column())
            elif expr_node_type == syms.star_expr:
                return self.handle_star_expr(expr_node)
            elif expr_node_type == syms.expr or \
                    expr_node_type == syms.xor_expr or \
                    expr_node_type == syms.and_expr or \
                    expr_node_type == syms.shift_expr or \
                    expr_node_type == syms.arith_expr or \
                    expr_node_type == syms.term:
                if expr_node.num_children() == 1:
                    expr_node = expr_node.get_child(0)
                    continue
                return self.handle_binop(expr_node)
            elif expr_node_type == syms.yield_expr:
                is_from = False
                if expr_node.num_children() > 1:
                    arg_node = expr_node.get_child(1)  # yield arg
                    if arg_node.num_children() == 2:
                        is_from = True
                        expr = self.handle_expr(arg_node.get_child(1))
                    else:
                        expr = self.handle_testlist(arg_node.get_child(0))
                else:
                    expr = None
                if is_from:
                    return ast.YieldFrom(expr, expr_node.get_lineno(), expr_node.get_column())
                return ast.Yield(expr, expr_node.get_lineno(), expr_node.get_column())
            elif expr_node_type == syms.factor:
                if expr_node.num_children() == 1:
                    expr_node = expr_node.get_child(0)
                    continue
                return self.handle_factor(expr_node)
            elif expr_node_type == syms.power:
                return self.handle_power(expr_node)
            else:
                raise AssertionError("unknown expr")

    def handle_star_expr(self, star_expr_node):
        expr = self.handle_expr(star_expr_node.get_child(1))
        return ast.Starred(expr, ast.Load, star_expr_node.get_lineno(),
                           star_expr_node.get_column())

    def handle_lambdef(self, lambdef_node):
        expr = self.handle_expr(lambdef_node.get_child(-1))
        if lambdef_node.num_children() == 3:
            args = ast.arguments(None, None, None, None, None, None)
        else:
            args = self.handle_arguments(lambdef_node.get_child(1))
        return ast.Lambda(args, expr, lambdef_node.get_lineno(), lambdef_node.get_column())

    def handle_ifexp(self, if_expr_node):
        body = self.handle_expr(if_expr_node.get_child(0))
        expression = self.handle_expr(if_expr_node.get_child(2))
        otherwise = self.handle_expr(if_expr_node.get_child(4))
        return ast.IfExp(expression, body, otherwise, if_expr_node.get_lineno(),
                         if_expr_node.get_column())

    def handle_comp_op(self, comp_op_node):
        comp_node = comp_op_node.get_child(0)
        comp_type = comp_node.type
        if comp_op_node.num_children() == 1:
            if comp_type == tokens.LESS:
                return ast.Lt
            elif comp_type == tokens.GREATER:
                return ast.Gt
            elif comp_type == tokens.EQEQUAL:
                return ast.Eq
            elif comp_type == tokens.LESSEQUAL:
                return ast.LtE
            elif comp_type == tokens.GREATEREQUAL:
                return ast.GtE
            elif comp_type == tokens.NOTEQUAL:
                flufl = self.compile_info.flags & consts.CO_FUTURE_BARRY_AS_BDFL
                if flufl and comp_node.get_value() == '!=':
                    self.error('invalid comparison', comp_node)
                elif not flufl and comp_node.get_value() == '<>':
                    self.error('invalid comparison', comp_node)
                return ast.NotEq
            elif comp_type == tokens.NAME:
                if comp_node.get_value() == "is":
                    return ast.Is
                elif comp_node.get_value() == "in":
                    return ast.In
                else:
                    raise AssertionError("invalid comparison")
            else:
                raise AssertionError("invalid comparison")
        else:
            if comp_op_node.get_child(1).get_value() == "in":
                return ast.NotIn
            elif comp_node.get_value() == "is":
                return ast.IsNot
            else:
                raise AssertionError("invalid comparison")

    def handle_binop(self, binop_node):
        left = self.handle_expr(binop_node.get_child(0))
        right = self.handle_expr(binop_node.get_child(2))
        op = operator_map(binop_node.get_child(1).type)
        result = ast.BinOp(left, op, right, binop_node.get_lineno(),
                           binop_node.get_column())
        number_of_ops = (binop_node.num_children() - 1) / 2
        for i in range(1, number_of_ops):
            op_node = binop_node.get_child(i * 2 + 1)
            op = operator_map(op_node.type)
            sub_right = self.handle_expr(binop_node.get_child(i * 2 + 2))
            result = ast.BinOp(result, op, sub_right, op_node.get_lineno(),
                               op_node.get_column())
        return result

    def handle_factor(self, factor_node):
        from pypy.interpreter.pyparser.parser import Terminal
        expr = self.handle_expr(factor_node.get_child(1))
        op_type = factor_node.get_child(0).type
        if op_type == tokens.PLUS:
            op = ast.UAdd
        elif op_type == tokens.MINUS:
            op = ast.USub
        elif op_type == tokens.TILDE:
            op = ast.Invert
        else:
            raise AssertionError("invalid factor node")
        return ast.UnaryOp(op, expr, factor_node.get_lineno(), factor_node.get_column())

    def handle_atom_expr(self, atom_node):
        start = 0
        num_ch = atom_node.num_children()
        if atom_node.get_child(0).type == tokens.AWAIT:
            start = 1
        atom_expr = self.handle_atom(atom_node.get_child(start))
        if num_ch == 1:
            return atom_expr
        if start and num_ch == 2:
            return ast.Await(atom_expr, atom_node.get_lineno(),
                             atom_node.get_column())
        for i in range(start+1, num_ch):
            trailer = atom_node.get_child(i)
            if trailer.type != syms.trailer:
                break
            tmp_atom_expr = self.handle_trailer(trailer, atom_expr)
            tmp_atom_expr.lineno = atom_expr.lineno
            tmp_atom_expr.col_offset = atom_expr.col_offset
            atom_expr = tmp_atom_expr
        if start:
            return ast.Await(atom_expr, atom_node.get_lineno(),
                             atom_node.get_column())
        else:
            return atom_expr
    
    def handle_power(self, power_node):
        atom_expr = self.handle_atom_expr(power_node.get_child(0))
        if power_node.num_children() == 1:
            return atom_expr
        if power_node.get_child(-1).type == syms.factor:
            right = self.handle_expr(power_node.get_child(-1))
            atom_expr = ast.BinOp(atom_expr, ast.Pow, right, power_node.get_lineno(),
                                  power_node.get_column())
        return atom_expr

    def handle_slice(self, slice_node):
        first_child = slice_node.get_child(0)
        if slice_node.num_children() == 1 and first_child.type == syms.test:
            index = self.handle_expr(first_child)
            return ast.Index(index)
        lower = None
        upper = None
        step = None
        if first_child.type == syms.test:
            lower = self.handle_expr(first_child)
        if first_child.type == tokens.COLON:
            if slice_node.num_children() > 1:
                second_child = slice_node.get_child(1)
                if second_child.type == syms.test:
                    upper = self.handle_expr(second_child)
        elif slice_node.num_children() > 2:
            third_child = slice_node.get_child(2)
            if third_child.type == syms.test:
                upper = self.handle_expr(third_child)
        last_child = slice_node.get_child(-1)
        if last_child.type == syms.sliceop:
            if last_child.num_children() != 1:
                step_child = last_child.get_child(1)
                if step_child.type == syms.test:
                    step = self.handle_expr(step_child)
        return ast.Slice(lower, upper, step)

    def handle_trailer(self, trailer_node, left_expr):
        first_child = trailer_node.get_child(0)
        if first_child.type == tokens.LPAR:
            if trailer_node.num_children() == 2:
                return ast.Call(left_expr, None, None,
                                trailer_node.get_lineno(), trailer_node.get_column())
            else:
                return self.handle_call(trailer_node.get_child(1), left_expr)
        elif first_child.type == tokens.DOT:
            attr = self.new_identifier(trailer_node.get_child(1).get_value())
            return ast.Attribute(left_expr, attr, ast.Load,
                                 trailer_node.get_lineno(), trailer_node.get_column())
        else:
            middle = trailer_node.get_child(1)
            if middle.num_children() == 1:
                slice = self.handle_slice(middle.get_child(0))
                return ast.Subscript(left_expr, slice, ast.Load,
                                     middle.get_lineno(), middle.get_column())
            slices = []
            simple = True
            for i in range(0, middle.num_children(), 2):
                slc = self.handle_slice(middle.get_child(i))
                if not isinstance(slc, ast.Index):
                    simple = False
                slices.append(slc)
            if not simple:
                ext_slice = ast.ExtSlice(slices)
                return ast.Subscript(left_expr, ext_slice, ast.Load,
                                     middle.get_lineno(), middle.get_column())
            elts = []
            for idx in slices:
                assert isinstance(idx, ast.Index)
                elts.append(idx.value)
            tup = ast.Tuple(elts, ast.Load, middle.get_lineno(), middle.get_column())
            return ast.Subscript(left_expr, ast.Index(tup), ast.Load,
                                 middle.get_lineno(), middle.get_column())

    def handle_call(self, args_node, callable_expr):
        arg_count = 0 # position args + iterable args unpackings
        keyword_count = 0 # keyword args + keyword args unpackings
        generator_count = 0 
        for i in range(args_node.num_children()):
            argument = args_node.get_child(i)
            if argument.type == syms.argument:
                if argument.num_children() == 1:
                    arg_count += 1
                elif argument.get_child(1).type == syms.comp_for:
                    generator_count += 1
                elif argument.get_child(0).type == tokens.STAR:
                    arg_count += 1
                else:
                    # argument.get_child(0).type == tokens.DOUBLESTAR
                    # or keyword arg
                    keyword_count += 1
        if generator_count > 1 or \
                (generator_count and (keyword_count or arg_count)):
            self.error("Generator expression must be parenthesized "
                       "if not sole argument", args_node)
        if arg_count + keyword_count + generator_count > 255:
            self.error("more than 255 arguments", args_node)
        args = []
        keywords = []
        used_keywords = {}
        doublestars_count = 0 # just keyword argument unpackings
        child_count = args_node.num_children()
        i = 0
        while i < child_count:
            argument = args_node.get_child(i)
            if argument.type == syms.argument:
                expr_node = argument.get_child(0)
                if argument.num_children() == 1:
                    # a positional argument
                    if keywords:
                        if doublestars_count:
                            self.error("positional argument follows "
                                       "keyword argument unpacking",
                                       expr_node)
                        else:
                            self.error("positional argument follows "
                                       "keyword argument",
                                       expr_node)
                    args.append(self.handle_expr(expr_node))
                elif expr_node.type == tokens.STAR:
                    # an iterable argument unpacking
                    if doublestars_count:
                        self.error("iterable argument unpacking follows "
                                   "keyword argument unpacking",
                                   expr_node)
                    expr = self.handle_expr(argument.get_child(1))
                    args.append(ast.Starred(expr, ast.Load,
                                            expr_node.get_lineno(),
                                            expr_node.get_column()))
                elif expr_node.type == tokens.DOUBLESTAR:
                    # a keyword argument unpacking
                    i += 1
                    expr = self.handle_expr(argument.get_child(1))
                    keywords.append(ast.keyword(None, expr))
                    doublestars_count += 1
                elif argument.get_child(1).type == syms.comp_for:
                    # the lone generator expression
                    args.append(self.handle_genexp(argument))
                else:
                    # a keyword argument
                    keyword_expr = self.handle_expr(expr_node)
                    if isinstance(keyword_expr, ast.Lambda):
                        self.error("lambda cannot contain assignment",
                                   expr_node)
                    elif not isinstance(keyword_expr, ast.Name):
                        self.error("keyword can't be an expression",
                                   expr_node)
                    keyword = keyword_expr.id
                    if keyword in used_keywords:
                        self.error("keyword argument repeated", expr_node)
                    used_keywords[keyword] = None
                    self.check_forbidden_name(keyword, expr_node)
                    keyword_value = self.handle_expr(argument.get_child(2))
                    keywords.append(ast.keyword(keyword, keyword_value))
            i += 1
        if not args:
            args = None
        if not keywords:
            keywords = None
        return ast.Call(callable_expr, args, keywords, callable_expr.lineno,
                        callable_expr.col_offset)

    def parse_number(self, raw):
        base = 10
        if raw.startswith("-"):
            negative = True
            raw = raw.lstrip("-")
        else:
            negative = False
        if raw.startswith("0"):
            if len(raw) > 2 and raw[1] in "Xx":
                base = 16
            elif len(raw) > 2 and raw[1] in "Bb":
                base = 2
            ## elif len(raw) > 2 and raw[1] in "Oo": # Fallback below is enough
            ##     base = 8
            elif len(raw) > 1:
                base = 8
            # strip leading characters
            i = 0
            limit = len(raw) - 1
            while i < limit:
                if base == 16 and raw[i] not in "0xX":
                    break
                if base == 8 and raw[i] not in "0oO":
                    break
                if base == 2 and raw[i] not in "0bB":
                    break
                i += 1
            raw = raw[i:]
            if not raw[0].isdigit():
                raw = "0" + raw
        if negative:
            raw = "-" + raw
        w_num_str = self.space.wrap(raw)
        w_base = self.space.wrap(base)
        if raw[-1] in "jJ":
            tp = self.space.w_complex
            return self.space.call_function(tp, w_num_str)
        try:
            return self.space.call_function(self.space.w_int, w_num_str, w_base)
        except error.OperationError as e:
            if not e.match(self.space, self.space.w_ValueError):
                raise
            return self.space.call_function(self.space.w_float, w_num_str)

    @always_inline
    def handle_dictelement(self, node, i):
        if node.get_child(i).type == tokens.DOUBLESTAR:
            key = None
            value = self.handle_expr(node.get_child(i+1))
            i += 2
        else:
            key = self.handle_expr(node.get_child(i))
            value = self.handle_expr(node.get_child(i+2))
            i += 3
        return (i,key,value)

    def handle_atom(self, atom_node):
        first_child = atom_node.get_child(0)
        first_child_type = first_child.type
        if first_child_type == tokens.NAME:
            name = first_child.get_value()
            if name == "None":
                w_singleton = self.space.w_None
            elif name == "True":
                w_singleton = self.space.w_True
            elif name == "False":
                w_singleton = self.space.w_False
            else:
                name = self.new_identifier(name)
                return ast.Name(name, ast.Load, first_child.get_lineno(),
                                first_child.get_column())
            return ast.NameConstant(w_singleton, first_child.get_lineno(),
                                first_child.get_column())
        #
        elif first_child_type == tokens.STRING:
            return fstring.string_parse_literal(self, atom_node)
        #
        elif first_child_type == tokens.NUMBER:
            num_value = self.parse_number(first_child.get_value())
            return ast.Num(num_value, atom_node.get_lineno(), atom_node.get_column())
        elif first_child_type == tokens.ELLIPSIS:
            return ast.Ellipsis(atom_node.get_lineno(), atom_node.get_column())
        elif first_child_type == tokens.LPAR:
            second_child = atom_node.get_child(1)
            if second_child.type == tokens.RPAR:
                return ast.Tuple(None, ast.Load, atom_node.get_lineno(),
                                 atom_node.get_column())
            elif second_child.type == syms.yield_expr:
                return self.handle_expr(second_child)
            return self.handle_testlist_gexp(second_child)
        elif first_child_type == tokens.LSQB:
            second_child = atom_node.get_child(1)
            if second_child.type == tokens.RSQB:
                return ast.List(None, ast.Load, atom_node.get_lineno(),
                                atom_node.get_column())
            if second_child.num_children() == 1 or \
                    second_child.get_child(1).type == tokens.COMMA:
                elts = self.get_expression_list(second_child)
                return ast.List(elts, ast.Load, atom_node.get_lineno(),
                                atom_node.get_column())
            return self.handle_listcomp(second_child)
        elif first_child_type == tokens.LBRACE:
            maker = atom_node.get_child(1)
            n_maker_children = maker.num_children()
            if maker.type == tokens.RBRACE:
                # an empty dict
                return ast.Dict(None, None, atom_node.get_lineno(), atom_node.get_column())
            else:
                is_dict = maker.get_child(0).type == tokens.DOUBLESTAR
                if (n_maker_children == 1 or
                    (n_maker_children > 1 and
                     maker.get_child(1).type == tokens.COMMA)):
                    # a set display
                    return self.handle_setdisplay(maker, atom_node)
                elif n_maker_children > 1 and maker.get_child(1).type == syms.comp_for:
                    # a set comprehension
                    return self.handle_setcomp(maker, atom_node)
                elif (n_maker_children > (3-is_dict) and
                      maker.get_child(3-is_dict).type == syms.comp_for):
                    # a dictionary comprehension
                    if is_dict:
                        raise self.error("dict unpacking cannot be used in "
                                         "dict comprehension", atom_node)
                    
                    return self.handle_dictcomp(maker, atom_node)
                else:
                    # a dictionary display
                    return self.handle_dictdisplay(maker, atom_node)
        else:
            raise AssertionError("unknown atom")

    def handle_testlist_gexp(self, gexp_node):
        if gexp_node.num_children() > 1 and \
                gexp_node.get_child(1).type == syms.comp_for:
            return self.handle_genexp(gexp_node)
        return self.handle_testlist(gexp_node)

    def count_comp_fors(self, comp_node):
        count = 0
        current_for = comp_node
        while True:
            count += 1
            if current_for.num_children() == 5:
                current_iter = current_for.get_child(4)
            else:
                return count
            while True:
                first_child = current_iter.get_child(0)
                if first_child.type == syms.comp_for:
                    current_for = current_iter.get_child(0)
                    break
                elif first_child.type == syms.comp_if:
                    if first_child.num_children() == 3:
                        current_iter = first_child.get_child(2)
                    else:
                        return count
                else:
                    raise AssertionError("should not reach here")

    def count_comp_ifs(self, iter_node):
        count = 0
        while True:
            first_child = iter_node.get_child(0)
            if first_child.type == syms.comp_for:
                return count
            count += 1
            if first_child.num_children() == 2:
                return count
            iter_node = first_child.get_child(2)

    def comprehension_helper(self, comp_node):
        fors_count = self.count_comp_fors(comp_node)
        comps = []
        for i in range(fors_count):
            for_node = comp_node.get_child(1)
            for_targets = self.handle_exprlist(for_node, ast.Store)
            expr = self.handle_expr(comp_node.get_child(3))
            assert isinstance(expr, ast.expr)
            if for_node.num_children() == 1:
                comp = ast.comprehension(for_targets[0], expr, None)
            else:
                # Modified in python2.7, see http://bugs.python.org/issue6704
                # Fixing unamed tuple location
                expr_node = for_targets[0]
                assert isinstance(expr_node, ast.expr)
                col = expr_node.col_offset
                line = expr_node.lineno
                target = ast.Tuple(for_targets, ast.Store, line, col)
                comp = ast.comprehension(target, expr, None)
            if comp_node.num_children() == 5:
                comp_node = comp_iter = comp_node.get_child(4)
                assert comp_iter.type == syms.comp_iter
                ifs_count = self.count_comp_ifs(comp_iter)
                if ifs_count:
                    ifs = []
                    for j in range(ifs_count):
                        comp_node = comp_if = comp_iter.get_child(0)
                        ifs.append(self.handle_expr(comp_if.get_child(1)))
                        if comp_if.num_children() == 3:
                            comp_node = comp_iter = comp_if.get_child(2)
                    comp.ifs = ifs
                if comp_node.type == syms.comp_iter:
                    comp_node = comp_node.get_child(0)
            assert isinstance(comp, ast.comprehension)
            comps.append(comp)
        return comps

    def handle_genexp(self, genexp_node):
        ch = genexp_node.get_child(0)
        elt = self.handle_expr(ch)
        if isinstance(elt, ast.Starred):
            self.error("iterable unpacking cannot be used in comprehension", ch)
        comps = self.comprehension_helper(genexp_node.get_child(1))
        return ast.GeneratorExp(elt, comps, genexp_node.get_lineno(),
                                genexp_node.get_column())

    def handle_listcomp(self, listcomp_node):
        ch = listcomp_node.get_child(0)
        elt = self.handle_expr(ch)
        if isinstance(elt, ast.Starred):
            self.error("iterable unpacking cannot be used in comprehension", ch)
        comps = self.comprehension_helper(listcomp_node.get_child(1))
        return ast.ListComp(elt, comps, listcomp_node.get_lineno(),
                            listcomp_node.get_column())

    def handle_setcomp(self, set_maker, atom_node):
        ch = set_maker.get_child(0)
        elt = self.handle_expr(ch)
        if isinstance(elt, ast.Starred):
            self.error("iterable unpacking cannot be used in comprehension", ch)
        comps = self.comprehension_helper(set_maker.get_child(1))
        return ast.SetComp(elt, comps, atom_node.get_lineno(),
                                       atom_node.get_column())

    def handle_dictcomp(self, dict_maker, atom_node):
        i, key, value = self.handle_dictelement(dict_maker, 0)
        comps = self.comprehension_helper(dict_maker.get_child(i))
        return ast.DictComp(key, value, comps, atom_node.get_lineno(),
                                               atom_node.get_column())
    
    def handle_dictdisplay(self, node, atom_node):
        keys = []
        values = []
        i = 0
        while i < node.num_children():
            i, key, value = self.handle_dictelement(node, i)
            keys.append(key)
            values.append(value)
            i += 1
        return ast.Dict(keys, values, atom_node.get_lineno(),
                                      atom_node.get_column())
    
    def handle_setdisplay(self, node, atom_node):
        elts = []
        i = 0
        while i < node.num_children():
            expr = self.handle_expr(node.get_child(i))
            elts.append(expr)
            i += 2
        return ast.Set(elts, atom_node.get_lineno(),
                             atom_node.get_column())

    def handle_exprlist(self, exprlist, context):
        exprs = []
        for i in range(0, exprlist.num_children(), 2):
            child = exprlist.get_child(i)
            expr = self.handle_expr(child)
            self.set_context(expr, context)
            exprs.append(expr)
        return exprs
