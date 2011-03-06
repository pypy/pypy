from pypy.interpreter.astcompiler import ast, consts, misc
from pypy.interpreter.astcompiler import asthelpers # Side effects
from pypy.interpreter import error
from pypy.interpreter.pyparser.pygram import syms, tokens
from pypy.interpreter.pyparser.error import SyntaxError
from pypy.interpreter.pyparser import parsestring
from pypy.rlib.objectmodel import specialize


def ast_from_node(space, node, compile_info):
    """Turn a parse tree, node, to AST."""
    return ASTBuilder(space, node, compile_info).build_ast()


augassign_operator_map = {
    '+='  : ast.Add,
    '-='  : ast.Sub,
    '/='  : ast.Div,
    '//=' : ast.FloorDiv,
    '%='  : ast.Mod,
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
    tokens.PERCENT : ast.Mod
})


class ASTBuilder(object):

    def __init__(self, space, n, compile_info):
        self.space = space
        self.compile_info = compile_info
        self.root_node = n

    def build_ast(self):
        """Convert an top level parse tree node into an AST mod."""
        n = self.root_node
        if n.type == syms.file_input:
            stmts = []
            for i in range(len(n.children) - 1):
                stmt = n.children[i]
                if stmt.type == tokens.NEWLINE:
                    continue
                sub_stmts_count = self.number_of_statements(stmt)
                if sub_stmts_count == 1:
                    stmts.append(self.handle_stmt(stmt))
                else:
                    stmt = stmt.children[0]
                    for j in range(sub_stmts_count):
                        small_stmt = stmt.children[j * 2]
                        stmts.append(self.handle_stmt(small_stmt))
            return ast.Module(stmts)
        elif n.type == syms.eval_input:
            body = self.handle_testlist(n.children[0])
            return ast.Expression(body)
        elif n.type == syms.single_input:
            first_child = n.children[0]
            if first_child.type == tokens.NEWLINE:
                # An empty line.
                return ast.Interactive([])
            else:
                num_stmts = self.number_of_statements(first_child)
                if num_stmts == 1:
                    stmts = [self.handle_stmt(first_child)]
                else:
                    stmts = []
                    for i in range(0, len(first_child.children), 2):
                        stmt = first_child.children[i]
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
            return self.number_of_statements(n.children[0])
        elif stmt_type == syms.simple_stmt:
            # Divide to remove semi-colons.
            return len(n.children) // 2
        else:
            raise AssertionError("non-statement node")

    def error(self, msg, n):
        """Raise a SyntaxError with the lineno and column set to n's."""
        raise SyntaxError(msg, n.lineno, n.column,
                          filename=self.compile_info.filename)

    def error_ast(self, msg, ast_node):
        raise SyntaxError(msg, ast_node.lineno, ast_node.col_offset,
                          filename=self.compile_info.filename)

    def check_forbidden_name(self, name, node):
        try:
            misc.check_forbidden_name(name)
        except misc.ForbiddenNameAssignment, e:
            self.error("cannot assign to %s" % (e.name,), node)

    def set_context(self, expr, ctx):
        """Set the context of an expression to Store or Del if possible."""
        try:
            expr.set_context(ctx)
        except ast.UnacceptableExpressionContext, e:
            self.error_ast(e.msg, e.node)
        except misc.ForbiddenNameAssignment, e:
            self.error_ast("cannot assign to %s" % (e.name,), e.node)

    def handle_print_stmt(self, print_node):
        dest = None
        expressions = None
        newline = True
        start = 1
        child_count = len(print_node.children)
        if child_count > 2 and print_node.children[1].type == tokens.RIGHTSHIFT:
            dest = self.handle_expr(print_node.children[2])
            start = 4
        if (child_count + 1 - start) // 2:
            expressions = [self.handle_expr(print_node.children[i])
                           for i in range(start, child_count, 2)]
        if print_node.children[-1].type == tokens.COMMA:
            newline = False
        return ast.Print(dest, expressions, newline, print_node.lineno,
                         print_node.column)

    def handle_del_stmt(self, del_node):
        targets = self.handle_exprlist(del_node.children[1], ast.Del)
        return ast.Delete(targets, del_node.lineno, del_node.column)

    def handle_flow_stmt(self, flow_node):
        first_child = flow_node.children[0]
        first_child_type = first_child.type
        if first_child_type == syms.break_stmt:
            return ast.Break(flow_node.lineno, flow_node.column)
        elif first_child_type == syms.continue_stmt:
            return ast.Continue(flow_node.lineno, flow_node.column)
        elif first_child_type == syms.yield_stmt:
            yield_expr = self.handle_expr(first_child.children[0])
            return ast.Expr(yield_expr, flow_node.lineno, flow_node.column)
        elif first_child_type == syms.return_stmt:
            if len(first_child.children) == 1:
                values = None
            else:
                values = self.handle_testlist(first_child.children[1])
            return ast.Return(values, flow_node.lineno, flow_node.column)
        elif first_child_type == syms.raise_stmt:
            exc = None
            value = None
            traceback = None
            child_count = len(first_child.children)
            if child_count >= 2:
                exc = self.handle_expr(first_child.children[1])
            if child_count >= 4:
                value = self.handle_expr(first_child.children[3])
            if child_count == 6:
                traceback = self.handle_expr(first_child.children[5])
            return ast.Raise(exc, value, traceback, flow_node.lineno,
                             flow_node.column)
        else:
            raise AssertionError("unknown flow statement")

    def alias_for_import_name(self, import_name, store=True):
        while True:
            import_name_type = import_name.type
            if import_name_type == syms.import_as_name:
                name = import_name.children[0].value
                if len(import_name.children) == 3:
                    as_name = import_name.children[2].value
                    self.check_forbidden_name(as_name, import_name.children[2])
                else:
                    as_name = None
                    self.check_forbidden_name(name, import_name.children[0])
                return ast.alias(name, as_name)
            elif import_name_type == syms.dotted_as_name:
                if len(import_name.children) == 1:
                    import_name = import_name.children[0]
                    continue
                alias = self.alias_for_import_name(import_name.children[0],
                                                   store=False)
                asname_node = import_name.children[2]
                alias.asname = asname_node.value
                self.check_forbidden_name(alias.asname, asname_node)
                return alias
            elif import_name_type == syms.dotted_name:
                if len(import_name.children) == 1:
                    name = import_name.children[0].value
                    if store:
                        self.check_forbidden_name(name, import_name.children[0])
                    return ast.alias(name, None)
                name_parts = [import_name.children[i].value
                              for i in range(0, len(import_name.children), 2)]
                name = ".".join(name_parts)
                return ast.alias(name, None)
            elif import_name_type == tokens.STAR:
                return ast.alias("*", None)
            else:
                raise AssertionError("unknown import name")

    def handle_import_stmt(self, import_node):
        import_node = import_node.children[0]
        if import_node.type == syms.import_name:
            dotted_as_names = import_node.children[1]
            aliases = [self.alias_for_import_name(dotted_as_names.children[i])
                       for i in range(0, len(dotted_as_names.children), 2)]
            return ast.Import(aliases, import_node.lineno, import_node.column)
        elif import_node.type == syms.import_from:
            child_count = len(import_node.children)
            module = None
            modname = None
            i = 1
            dot_count = 0
            while i < child_count:
                child = import_node.children[i]
                if child.type == syms.dotted_name:
                    module = self.alias_for_import_name(child, False)
                    i += 1
                    break
                elif child.type != tokens.DOT:
                    break
                i += 1
                dot_count += 1
            i += 1
            after_import_type = import_node.children[i].type
            star_import = False
            if after_import_type == tokens.STAR:
                names_node = import_node.children[i]
                star_import = True
            elif after_import_type == tokens.LPAR:
                names_node = import_node.children[i + 1]
            elif after_import_type == syms.import_as_names:
                names_node = import_node.children[i]
                if len(names_node.children) % 2 == 0:
                    self.error("trailing comma is only allowed with "
                               "surronding parenthesis", names_node)
            else:
                raise AssertionError("unknown import node")
            if star_import:
                aliases = [self.alias_for_import_name(names_node)]
            else:
                aliases = [self.alias_for_import_name(names_node.children[i])
                           for i in range(0, len(names_node.children), 2)]
            if module is not None:
                modname = module.name
            return ast.ImportFrom(modname, aliases, dot_count,
                                  import_node.lineno, import_node.column)
        else:
            raise AssertionError("unknown import node")

    def handle_global_stmt(self, global_node):
        names = [global_node.children[i].value
                 for i in range(1, len(global_node.children), 2)]
        return ast.Global(names, global_node.lineno, global_node.column)

    def handle_exec_stmt(self, exec_node):
        child_count = len(exec_node.children)
        globs = None
        locs = None
        to_execute = self.handle_expr(exec_node.children[1])
        if child_count >= 4:
            globs = self.handle_expr(exec_node.children[3])
        if child_count == 6:
            locs = self.handle_expr(exec_node.children[5])
        return ast.Exec(to_execute, globs, locs, exec_node.lineno,
                        exec_node.column)

    def handle_assert_stmt(self, assert_node):
        child_count = len(assert_node.children)
        expr = self.handle_expr(assert_node.children[1])
        msg = None
        if len(assert_node.children) == 4:
            msg = self.handle_expr(assert_node.children[3])
        return ast.Assert(expr, msg, assert_node.lineno, assert_node.column)

    def handle_suite(self, suite_node):
        first_child = suite_node.children[0]
        if first_child.type == syms.simple_stmt:
            end = len(first_child.children) - 1
            if first_child.children[end - 1].type == tokens.SEMI:
                end -= 1
            stmts = [self.handle_stmt(first_child.children[i])
                     for i in range(0, end, 2)]
        else:
            stmts = []
            for i in range(2, len(suite_node.children) - 1):
                stmt = suite_node.children[i]
                stmt_count = self.number_of_statements(stmt)
                if stmt_count == 1:
                    stmts.append(self.handle_stmt(stmt))
                else:
                    simple_stmt = stmt.children[0]
                    for j in range(0, len(simple_stmt.children), 2):
                        stmt = simple_stmt.children[j]
                        if not stmt.children:
                            break
                        stmts.append(self.handle_stmt(stmt))
        return stmts

    def handle_if_stmt(self, if_node):
        child_count = len(if_node.children)
        if child_count == 4:
            test = self.handle_expr(if_node.children[1])
            suite = self.handle_suite(if_node.children[3])
            return ast.If(test, suite, None, if_node.lineno, if_node.column)
        otherwise_string = if_node.children[4].value
        if otherwise_string == "else":
            test = self.handle_expr(if_node.children[1])
            suite = self.handle_suite(if_node.children[3])
            else_suite = self.handle_suite(if_node.children[6])
            return ast.If(test, suite, else_suite, if_node.lineno,
                          if_node.column)
        elif otherwise_string == "elif":
            elif_count = child_count - 4
            after_elif = if_node.children[elif_count + 1]
            if after_elif.type == tokens.NAME and \
                    after_elif.value == "else":
                has_else = True
                elif_count -= 3
            else:
                has_else = False
            elif_count /= 4
            if has_else:
                last_elif = if_node.children[-6]
                last_elif_test = self.handle_expr(last_elif)
                elif_body = self.handle_suite(if_node.children[-4])
                else_body = self.handle_suite(if_node.children[-1])
                otherwise = [ast.If(last_elif_test, elif_body, else_body,
                                    last_elif.lineno, last_elif.column)]
                elif_count -= 1
            else:
                otherwise = None
            for i in range(elif_count):
                offset = 5 + (elif_count - i - 1) * 4
                elif_test_node = if_node.children[offset]
                elif_test = self.handle_expr(elif_test_node)
                elif_body = self.handle_suite(if_node.children[offset + 2])
                new_if = ast.If(elif_test, elif_body, otherwise,
                                elif_test_node.lineno, elif_test_node.column)
                otherwise = [new_if]
            expr = self.handle_expr(if_node.children[1])
            body = self.handle_suite(if_node.children[3])
            return ast.If(expr, body, otherwise, if_node.lineno, if_node.column)
        else:
            raise AssertionError("unknown if statement configuration")

    def handle_while_stmt(self, while_node):
        loop_test = self.handle_expr(while_node.children[1])
        body = self.handle_suite(while_node.children[3])
        if len(while_node.children) == 7:
            otherwise = self.handle_suite(while_node.children[6])
        else:
            otherwise = None
        return ast.While(loop_test, body, otherwise, while_node.lineno,
                         while_node.column)

    def handle_for_stmt(self, for_node):
        target_node = for_node.children[1]
        target_as_exprlist = self.handle_exprlist(target_node, ast.Store)
        if len(target_node.children) == 1:
            target = target_as_exprlist[0]
        else:
            target = ast.Tuple(target_as_exprlist, ast.Store,
                               target_node.lineno, target_node.column)
        expr = self.handle_testlist(for_node.children[3])
        body = self.handle_suite(for_node.children[5])
        if len(for_node.children) == 9:
            otherwise = self.handle_suite(for_node.children[8])
        else:
            otherwise = None
        return ast.For(target, expr, body, otherwise, for_node.lineno,
                       for_node.column)

    def handle_except_clause(self, exc, body):
        test = None
        target = None
        suite = self.handle_suite(body)
        child_count = len(exc.children)
        if child_count >= 2:
            test = self.handle_expr(exc.children[1])
        if child_count == 4:
            target_child = exc.children[3]
            target = self.handle_expr(target_child)
            self.set_context(target, ast.Store)
        return ast.ExceptHandler(test, target, suite, exc.lineno, exc.column)

    def handle_try_stmt(self, try_node):
        body = self.handle_suite(try_node.children[2])
        child_count = len(try_node.children)
        except_count = (child_count - 3 ) // 3
        otherwise = None
        finally_suite = None
        possible_extra_clause = try_node.children[-3]
        if possible_extra_clause.type == tokens.NAME:
            if possible_extra_clause.value == "finally":
                if child_count >= 9 and \
                        try_node.children[-6].type == tokens.NAME:
                    otherwise = self.handle_suite(try_node.children[-4])
                    except_count -= 1
                finally_suite = self.handle_suite(try_node.children[-1])
                except_count -= 1
            else:
                otherwise = self.handle_suite(try_node.children[-1])
                except_count -= 1
        if except_count:
            handlers = []
            for i in range(except_count):
                base_offset = i * 3
                exc = try_node.children[3 + base_offset]
                except_body = try_node.children[5 + base_offset]
                handlers.append(self.handle_except_clause(exc, except_body))
            except_ast = ast.TryExcept(body, handlers, otherwise,
                                       try_node.lineno, try_node.column)
            if finally_suite is None:
                return except_ast
            body = [except_ast]
        return ast.TryFinally(body, finally_suite, try_node.lineno,
                              try_node.column)

    def handle_with_stmt(self, with_node):
        body = self.handle_suite(with_node.children[-1])
        i = len(with_node.children) - 1
        while True:
            i -= 2
            item = with_node.children[i]
            test = self.handle_expr(item.children[0])
            if len(item.children) == 3:
                target = self.handle_expr(item.children[2])
                self.set_context(target, ast.Store)
            else:
                target = None
            wi = ast.With(test, target, body, with_node.lineno,
                          with_node.column)
            if i == 1:
                break
            body = [wi]
        return wi

    def handle_classdef(self, classdef_node, decorators=None):
        name_node = classdef_node.children[1]
        name = name_node.value
        self.check_forbidden_name(name, name_node)
        if len(classdef_node.children) == 4:
            body = self.handle_suite(classdef_node.children[3])
            return ast.ClassDef(name, None, body, decorators,
                                classdef_node.lineno, classdef_node.column)
        if classdef_node.children[3].type == tokens.RPAR:
            body = self.handle_suite(classdef_node.children[5])
            return ast.ClassDef(name, None, body, decorators,
                                classdef_node.lineno, classdef_node.column)
        bases = self.handle_class_bases(classdef_node.children[3])
        body = self.handle_suite(classdef_node.children[6])
        return ast.ClassDef(name, bases, body, decorators, classdef_node.lineno,
                            classdef_node.column)

    def handle_class_bases(self, bases_node):
        if len(bases_node.children) == 1:
            return [self.handle_expr(bases_node.children[0])]
        return self.get_expression_list(bases_node)

    def handle_funcdef(self, funcdef_node, decorators=None):
        name_node = funcdef_node.children[1]
        name = name_node.value
        self.check_forbidden_name(name, name_node)
        args = self.handle_arguments(funcdef_node.children[2])
        body = self.handle_suite(funcdef_node.children[4])
        return ast.FunctionDef(name, args, body, decorators,
                               funcdef_node.lineno, funcdef_node.column)

    def handle_decorated(self, decorated_node):
        decorators = self.handle_decorators(decorated_node.children[0])
        definition = decorated_node.children[1]
        if definition.type == syms.funcdef:
            node = self.handle_funcdef(definition, decorators)
        elif definition.type == syms.classdef:
            node = self.handle_classdef(definition, decorators)
        else:
            raise AssertionError("unkown decorated")
        node.lineno = decorated_node.lineno
        node.col_offset = decorated_node.column
        return node

    def handle_decorators(self, decorators_node):
        return [self.handle_decorator(dec) for dec in decorators_node.children]

    def handle_decorator(self, decorator_node):
        dec_name = self.handle_dotted_name(decorator_node.children[1])
        if len(decorator_node.children) == 3:
            dec = dec_name
        elif len(decorator_node.children) == 5:
            dec = ast.Call(dec_name, None, None, None, None,
                           decorator_node.lineno, decorator_node.column)
        else:
            dec = self.handle_call(decorator_node.children[3], dec_name)
        return dec

    def handle_dotted_name(self, dotted_name_node):
        base_value = dotted_name_node.children[0].value
        name = ast.Name(base_value, ast.Load, dotted_name_node.lineno,
                        dotted_name_node.column)
        for i in range(2, len(dotted_name_node.children), 2):
            attr = dotted_name_node.children[i].value
            name = ast.Attribute(name, attr, ast.Load, dotted_name_node.lineno,
                                 dotted_name_node.column)
        return name

    def handle_arguments(self, arguments_node):
        if arguments_node.type == syms.parameters:
            if len(arguments_node.children) == 2:
                return ast.arguments(None, None, None, None)
            arguments_node = arguments_node.children[1]
        i = 0
        child_count = len(arguments_node.children)
        defaults = []
        args = []
        variable_arg = None
        keywords_arg = None
        have_default = False
        while i < child_count:
            argument = arguments_node.children[i]
            arg_type = argument.type
            if arg_type == syms.fpdef:
                parenthesized = False
                complex_args = False
                while True:
                    if i + 1 < child_count and \
                            arguments_node.children[i + 1].type == tokens.EQUAL:
                        default_node = arguments_node.children[i + 2]
                        defaults.append(self.handle_expr(default_node))
                        i += 2
                        have_default = True
                    elif have_default:
                        if parenthesized and not complex_args:
                            msg = "parenthesized arg with default"
                        else:
                            msg = ("non-default argument follows default "
                                   "argument")
                        self.error(msg, arguments_node)
                    if len(argument.children) == 3:
                        sub_arg = argument.children[1]
                        if len(sub_arg.children) != 1:
                            complex_args = True
                            args.append(self.handle_arg_unpacking(sub_arg))
                        else:
                            parenthesized = True
                            argument = sub_arg.children[0]
                            continue
                    if argument.children[0].type == tokens.NAME:
                        name_node = argument.children[0]
                        arg_name = name_node.value
                        self.check_forbidden_name(arg_name, name_node)
                        name = ast.Name(arg_name, ast.Param, name_node.lineno,
                                        name_node.column)
                        args.append(name)
                    i += 2
                    break
            elif arg_type == tokens.STAR:
                name_node = arguments_node.children[i + 1]
                variable_arg = name_node.value
                self.check_forbidden_name(variable_arg, name_node)
                i += 3
            elif arg_type == tokens.DOUBLESTAR:
                name_node = arguments_node.children[i + 1]
                keywords_arg = name_node.value
                self.check_forbidden_name(keywords_arg, name_node)
                i += 3
            else:
                raise AssertionError("unknown node in argument list")
        if not defaults:
            defaults = None
        if not args:
            args = None
        return ast.arguments(args, variable_arg, keywords_arg, defaults)

    def handle_arg_unpacking(self, fplist_node):
        args = []
        for i in range((len(fplist_node.children) + 1) / 2):
            fpdef_node = fplist_node.children[i * 2]
            while True:
                child = fpdef_node.children[0]
                if child.type == tokens.NAME:
                    arg = ast.Name(child.value, ast.Store, child.lineno,
                                   child.column)
                    args.append(arg)
                else:
                    child = fpdef_node.children[1]
                    if len(child.children) == 1:
                        fpdef_node = child.children[0]
                        continue
                    args.append(self.handle_arg_unpacking(child))
                break
        tup = ast.Tuple(args, ast.Store, fplist_node.lineno, fplist_node.column)
        self.set_context(tup, ast.Store)
        return tup

    def handle_stmt(self, stmt):
        stmt_type = stmt.type
        if stmt_type == syms.stmt:
            stmt = stmt.children[0]
            stmt_type = stmt.type
        if stmt_type == syms.simple_stmt:
            stmt = stmt.children[0]
            stmt_type = stmt.type
        if stmt_type == syms.small_stmt:
            stmt = stmt.children[0]
            stmt_type = stmt.type
            if stmt_type == syms.expr_stmt:
                return self.handle_expr_stmt(stmt)
            elif stmt_type == syms.print_stmt:
                return self.handle_print_stmt(stmt)
            elif stmt_type == syms.del_stmt:
                return self.handle_del_stmt(stmt)
            elif stmt_type == syms.pass_stmt:
                return ast.Pass(stmt.lineno, stmt.column)
            elif stmt_type == syms.flow_stmt:
                return self.handle_flow_stmt(stmt)
            elif stmt_type == syms.import_stmt:
                return self.handle_import_stmt(stmt)
            elif stmt_type == syms.global_stmt:
                return self.handle_global_stmt(stmt)
            elif stmt_type == syms.assert_stmt:
                return self.handle_assert_stmt(stmt)
            elif stmt_type == syms.exec_stmt:
                return self.handle_exec_stmt(stmt)
            else:
                raise AssertionError("unhandled small statement")
        elif stmt_type == syms.compound_stmt:
            stmt = stmt.children[0]
            stmt_type = stmt.type
            if stmt_type == syms.if_stmt:
                return self.handle_if_stmt(stmt)
            elif stmt_type == syms.while_stmt:
                return self.handle_while_stmt(stmt)
            elif stmt_type == syms.for_stmt:
                return self.handle_for_stmt(stmt)
            elif stmt_type == syms.try_stmt:
                return self.handle_try_stmt(stmt)
            elif stmt_type == syms.with_stmt:
                return self.handle_with_stmt(stmt)
            elif stmt_type == syms.funcdef:
                return self.handle_funcdef(stmt)
            elif stmt_type == syms.classdef:
                return self.handle_classdef(stmt)
            elif stmt_type == syms.decorated:
                return self.handle_decorated(stmt)
            else:
                raise AssertionError("unhandled compound statement")
        else:
            raise AssertionError("unknown statment type")

    def handle_expr_stmt(self, stmt):
        if len(stmt.children) == 1:
            expression = self.handle_testlist(stmt.children[0])
            return ast.Expr(expression, stmt.lineno, stmt.column)
        elif stmt.children[1].type == syms.augassign:
            # Augmented assignment.
            target_child = stmt.children[0]
            target_expr = self.handle_testlist(target_child)
            self.set_context(target_expr, ast.Store)
            value_child = stmt.children[2]
            if value_child.type == syms.testlist:
                value_expr = self.handle_testlist(value_child)
            else:
                value_expr = self.handle_expr(value_child)
            op_str = stmt.children[1].children[0].value
            operator = augassign_operator_map[op_str]
            return ast.AugAssign(target_expr, operator, value_expr,
                                 stmt.lineno, stmt.column)
        else:
            # Normal assignment.
            targets = []
            for i in range(0, len(stmt.children) - 2, 2):
                target_node = stmt.children[i]
                if target_node.type == syms.yield_expr:
                    self.error("can't assign to yield expression", target_node)
                target_expr = self.handle_testlist(target_node)
                self.set_context(target_expr, ast.Store)
                targets.append(target_expr)
            value_child = stmt.children[-1]
            if value_child.type == syms.testlist:
                value_expr = self.handle_testlist(value_child)
            else:
                value_expr = self.handle_expr(value_child)
            return ast.Assign(targets, value_expr, stmt.lineno, stmt.column)

    def get_expression_list(self, tests):
        return [self.handle_expr(tests.children[i])
                for i in range(0, len(tests.children), 2)]

    def handle_testlist(self, tests):
        if len(tests.children) == 1:
            return self.handle_expr(tests.children[0])
        else:
            elts = self.get_expression_list(tests)
            return ast.Tuple(elts, ast.Load, tests.lineno, tests.column)

    def handle_expr(self, expr_node):
        # Loop until we return something.
        while True:
            expr_node_type = expr_node.type
            if expr_node_type == syms.test or expr_node_type == syms.old_test:
                first_child = expr_node.children[0]
                if first_child.type in (syms.lambdef, syms.old_lambdef):
                    return self.handle_lambdef(first_child)
                elif len(expr_node.children) > 1:
                    return self.handle_ifexp(expr_node)
                else:
                    expr_node = first_child
            elif expr_node_type == syms.or_test or \
                    expr_node_type == syms.and_test:
                if len(expr_node.children) == 1:
                    expr_node = expr_node.children[0]
                    continue
                seq = [self.handle_expr(expr_node.children[i])
                       for i in range(0, len(expr_node.children), 2)]
                if expr_node_type == syms.or_test:
                    op = ast.Or
                else:
                    op = ast.And
                return ast.BoolOp(op, seq, expr_node.lineno, expr_node.column)
            elif expr_node_type == syms.not_test:
                if len(expr_node.children) == 1:
                    expr_node = expr_node.children[0]
                    continue
                expr = self.handle_expr(expr_node.children[1])
                return ast.UnaryOp(ast.Not, expr, expr_node.lineno,
                                   expr_node.column)
            elif expr_node_type == syms.comparison:
                if len(expr_node.children) == 1:
                    expr_node = expr_node.children[0]
                    continue
                operators = []
                operands = []
                expr = self.handle_expr(expr_node.children[0])
                for i in range(1, len(expr_node.children), 2):
                    operators.append(self.handle_comp_op(expr_node.children[i]))
                    operands.append(self.handle_expr(expr_node.children[i + 1]))
                return ast.Compare(expr, operators, operands, expr_node.lineno,
                                   expr_node.column)
            elif expr_node_type == syms.expr or \
                    expr_node_type == syms.xor_expr or \
                    expr_node_type == syms.and_expr or \
                    expr_node_type == syms.shift_expr or \
                    expr_node_type == syms.arith_expr or \
                    expr_node_type == syms.term:
                if len(expr_node.children) == 1:
                    expr_node = expr_node.children[0]
                    continue
                return self.handle_binop(expr_node)
            elif expr_node_type == syms.yield_expr:
                if len(expr_node.children) == 2:
                    exp = self.handle_testlist(expr_node.children[1])
                else:
                    exp = None
                return ast.Yield(exp, expr_node.lineno, expr_node.column)
            elif expr_node_type == syms.factor:
                if len(expr_node.children) == 1:
                    expr_node = expr_node.children[0]
                    continue
                return self.handle_factor(expr_node)
            elif expr_node_type == syms.power:
                return self.handle_power(expr_node)
            else:
                raise AssertionError("unknown expr")

    def handle_lambdef(self, lambdef_node):
        expr = self.handle_expr(lambdef_node.children[-1])
        if len(lambdef_node.children) == 3:
            args = ast.arguments(None, None, None, None)
        else:
            args = self.handle_arguments(lambdef_node.children[1])
        return ast.Lambda(args, expr, lambdef_node.lineno, lambdef_node.column)

    def handle_ifexp(self, if_expr_node):
        body = self.handle_expr(if_expr_node.children[0])
        expression = self.handle_expr(if_expr_node.children[2])
        otherwise = self.handle_expr(if_expr_node.children[4])
        return ast.IfExp(expression, body, otherwise, if_expr_node.lineno,
                         if_expr_node.column)

    def handle_comp_op(self, comp_op_node):
        comp_node = comp_op_node.children[0]
        comp_type = comp_node.type
        if len(comp_op_node.children) == 1:
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
                return ast.NotEq
            elif comp_type == tokens.NAME:
                if comp_node.value == "is":
                    return ast.Is
                elif comp_node.value == "in":
                    return ast.In
                else:
                    raise AssertionError("invalid comparison")
            else:
                raise AssertionError("invalid comparison")
        else:
            if comp_op_node.children[1].value == "in":
                return ast.NotIn
            elif comp_node.value == "is":
                return ast.IsNot
            else:
                raise AssertionError("invalid comparison")

    def handle_binop(self, binop_node):
        left = self.handle_expr(binop_node.children[0])
        right = self.handle_expr(binop_node.children[2])
        op = operator_map(binop_node.children[1].type)
        result = ast.BinOp(left, op, right, binop_node.lineno,
                           binop_node.column)
        number_of_ops = (len(binop_node.children) - 1) / 2
        for i in range(1, number_of_ops):
            op_node = binop_node.children[i * 2 + 1]
            op = operator_map(op_node.type)
            sub_right = self.handle_expr(binop_node.children[i * 2 + 2])
            result = ast.BinOp(result, op, sub_right, op_node.lineno,
                               op_node.column)
        return result

    def handle_factor(self, factor_node):
        # Fold '-' on constant numbers.
        if factor_node.children[0].type == tokens.MINUS and \
                len(factor_node.children) == 2:
            factor = factor_node.children[1]
            if factor.type == syms.factor and len(factor.children) == 1:
                power = factor.children[0]
                if power.type == syms.power and len(power.children) == 1:
                    atom = power.children[0]
                    if atom.type == syms.atom and \
                            atom.children[0].type == tokens.NUMBER:
                        num = atom.children[0]
                        num.value = "-" + num.value
                        return self.handle_atom(atom)
        expr = self.handle_expr(factor_node.children[1])
        op_type = factor_node.children[0].type
        if op_type == tokens.PLUS:
            op = ast.UAdd
        elif op_type == tokens.MINUS:
            op = ast.USub
        elif op_type == tokens.TILDE:
            op = ast.Invert
        else:
            raise AssertionError("invalid factor node")
        return ast.UnaryOp(op, expr, factor_node.lineno, factor_node.column)

    def handle_power(self, power_node):
        atom_expr = self.handle_atom(power_node.children[0])
        if len(power_node.children) == 1:
            return atom_expr
        for i in range(1, len(power_node.children)):
            trailer = power_node.children[i]
            if trailer.type != syms.trailer:
                break
            tmp_atom_expr = self.handle_trailer(trailer, atom_expr)
            tmp_atom_expr.lineno = atom_expr.lineno
            tmp_atom_expr.col_offset = atom_expr.col_offset
            atom_expr = tmp_atom_expr
        if power_node.children[-1].type == syms.factor:
            right = self.handle_expr(power_node.children[-1])
            atom_expr = ast.BinOp(atom_expr, ast.Pow, right, power_node.lineno,
                                  power_node.column)
        return atom_expr

    def handle_slice(self, slice_node):
        first_child = slice_node.children[0]
        if first_child.type == tokens.DOT:
            return ast.Ellipsis()
        if len(slice_node.children) == 1 and first_child.type == syms.test:
            index = self.handle_expr(first_child)
            return ast.Index(index)
        lower = None
        upper = None
        step = None
        if first_child.type == syms.test:
            lower = self.handle_expr(first_child)
        if first_child.type == tokens.COLON:
            if len(slice_node.children) > 1:
                second_child = slice_node.children[1]
                if second_child.type == syms.test:
                    upper = self.handle_expr(second_child)
        elif len(slice_node.children) > 2:
            third_child = slice_node.children[2]
            if third_child.type == syms.test:
                upper = self.handle_expr(third_child)
        last_child = slice_node.children[-1]
        if last_child.type == syms.sliceop:
            if len(last_child.children) == 1:
                step = ast.Name("None", ast.Load, last_child.lineno,
                                last_child.column)
            else:
                step_child = last_child.children[1]
                if step_child.type == syms.test:
                    step = self.handle_expr(step_child)
        return ast.Slice(lower, upper, step)

    def handle_trailer(self, trailer_node, left_expr):
        first_child = trailer_node.children[0]
        if first_child.type == tokens.LPAR:
            if len(trailer_node.children) == 2:
                return ast.Call(left_expr, None, None, None, None,
                                trailer_node.lineno, trailer_node.column)
            else:
                return self.handle_call(trailer_node.children[1], left_expr)
        elif first_child.type == tokens.DOT:
            attr = trailer_node.children[1].value
            return ast.Attribute(left_expr, attr, ast.Load,
                                 trailer_node.lineno, trailer_node.column)
        else:
            middle = trailer_node.children[1]
            if len(middle.children) == 1:
                slice = self.handle_slice(middle.children[0])
                return ast.Subscript(left_expr, slice, ast.Load,
                                     middle.lineno, middle.column)
            slices = []
            simple = True
            for i in range(0, len(middle.children), 2):
                slc = self.handle_slice(middle.children[i])
                if not isinstance(slc, ast.Index):
                    simple = False
                slices.append(slc)
            if not simple:
                ext_slice = ast.ExtSlice(slices)
                return ast.Subscript(left_expr, ext_slice, ast.Load,
                                     middle.lineno, middle.column)
            elts = []
            for idx in slices:
                assert isinstance(idx, ast.Index)
                elts.append(idx.value)
            tup = ast.Tuple(elts, ast.Load, middle.lineno, middle.column)
            return ast.Subscript(left_expr, ast.Index(tup), ast.Load,
                                 middle.lineno, middle.column)

    def handle_call(self, args_node, callable_expr):
        arg_count = 0
        keyword_count = 0
        generator_count = 0
        for argument in args_node.children:
            if argument.type == syms.argument:
                if len(argument.children) == 1:
                    arg_count += 1
                elif argument.children[1].type == syms.comp_for:
                    generator_count += 1
                else:
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
        variable_arg = None
        keywords_arg = None
        child_count = len(args_node.children)
        i = 0
        while i < child_count:
            argument = args_node.children[i]
            if argument.type == syms.argument:
                if len(argument.children) == 1:
                    expr_node = argument.children[0]
                    if keywords:
                        self.error("non-keyword arg after keyword arg",
                                   expr_node)
                    if variable_arg:
                        self.error("only named arguments may follow "
                                   "*expression", expr_node)
                    args.append(self.handle_expr(expr_node))
                elif argument.children[1].type == syms.comp_for:
                    args.append(self.handle_genexp(argument))
                else:
                    keyword_node = argument.children[0]
                    keyword_expr = self.handle_expr(keyword_node)
                    if isinstance(keyword_expr, ast.Lambda):
                        self.error("lambda cannot contain assignment",
                                   keyword_node)
                    elif not isinstance(keyword_expr, ast.Name):
                        self.error("keyword can't be an expression",
                                   keyword_node)
                    keyword = keyword_expr.id
                    if keyword in used_keywords:
                        self.error("keyword argument repeated", keyword_node)
                    used_keywords[keyword] = None
                    self.check_forbidden_name(keyword, keyword_node)
                    keyword_value = self.handle_expr(argument.children[2])
                    keywords.append(ast.keyword(keyword, keyword_value))
            elif argument.type == tokens.STAR:
                variable_arg = self.handle_expr(args_node.children[i + 1])
                i += 1
            elif argument.type == tokens.DOUBLESTAR:
                keywords_arg = self.handle_expr(args_node.children[i + 1])
                i += 1
            i += 1
        if not args:
            args = None
        if not keywords:
            keywords = None
        return ast.Call(callable_expr, args, keywords, variable_arg,
                        keywords_arg, callable_expr.lineno,
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
        w_index = None
        w_base = self.space.wrap(base)
        if raw[-1] in "lL":
            tp = self.space.w_long
            return self.space.call_function(tp, w_num_str, w_base)
        elif raw[-1] in "jJ":
            tp = self.space.w_complex
            return self.space.call_function(tp, w_num_str)
        try:
            return self.space.call_function(self.space.w_int, w_num_str, w_base)
        except error.OperationError, e:
            if not e.match(self.space, self.space.w_ValueError):
                raise
            return self.space.call_function(self.space.w_float, w_num_str)

    def handle_atom(self, atom_node):
        first_child = atom_node.children[0]
        first_child_type = first_child.type
        if first_child_type == tokens.NAME:
            return ast.Name(first_child.value, ast.Load,
                            first_child.lineno, first_child.column)
        elif first_child_type == tokens.STRING:
            space = self.space
            encoding = self.compile_info.encoding
            flags = self.compile_info.flags
            unicode_literals = flags & consts.CO_FUTURE_UNICODE_LITERALS
            try:
                sub_strings_w = [parsestring.parsestr(space, encoding, s.value,
                                                      unicode_literals)
                                 for s in atom_node.children]
            except error.OperationError, e:
                if not e.match(space, space.w_UnicodeError):
                    raise
                # UnicodeError in literal: turn into SyntaxError
                self.error(e.errorstr(space), atom_node)
                sub_strings_w = [] # please annotator
            # This implements implicit string concatenation.
            if len(sub_strings_w) > 1:
                w_sub_strings = space.newlist(sub_strings_w)
                w_join = space.getattr(space.wrap(""), space.wrap("join"))
                final_string = space.call_function(w_join, w_sub_strings)
            else:
                final_string = sub_strings_w[0]
            return ast.Str(final_string, atom_node.lineno, atom_node.column)
        elif first_child_type == tokens.NUMBER:
            num_value = self.parse_number(first_child.value)
            return ast.Num(num_value, atom_node.lineno, atom_node.column)
        elif first_child_type == tokens.LPAR:
            second_child = atom_node.children[1]
            if second_child.type == tokens.RPAR:
                return ast.Tuple(None, ast.Load, atom_node.lineno,
                                 atom_node.column)
            elif second_child.type == syms.yield_expr:
                return self.handle_expr(second_child)
            return self.handle_testlist_gexp(second_child)
        elif first_child_type == tokens.LSQB:
            second_child = atom_node.children[1]
            if second_child.type == tokens.RSQB:
                return ast.List(None, ast.Load, atom_node.lineno,
                                atom_node.column)
            if len(second_child.children) == 1 or \
                    second_child.children[1].type == tokens.COMMA:
                elts = self.get_expression_list(second_child)
                return ast.List(elts, ast.Load, atom_node.lineno,
                                atom_node.column)
            return self.handle_listcomp(second_child)
        elif first_child_type == tokens.LBRACE:
            maker = atom_node.children[1]
            if maker.type == tokens.RBRACE:
                return ast.Dict(None, None, atom_node.lineno, atom_node.column)
            n_maker_children = len(maker.children)
            if n_maker_children == 1 or maker.children[1].type == tokens.COMMA:
                elts = []
                for i in range(0, n_maker_children, 2):
                    elts.append(self.handle_expr(maker.children[i]))
                return ast.Set(elts, atom_node.lineno, atom_node.column)
            if maker.children[1].type == syms.comp_for:
                return self.handle_setcomp(maker)
            if (n_maker_children > 3 and
                maker.children[3].type == syms.comp_for):
                return self.handle_dictcomp(maker)
            keys = []
            values = []
            for i in range(0, n_maker_children, 4):
                keys.append(self.handle_expr(maker.children[i]))
                values.append(self.handle_expr(maker.children[i + 2]))
            return ast.Dict(keys, values, atom_node.lineno, atom_node.column)
        elif first_child_type == tokens.BACKQUOTE:
            expr = self.handle_testlist(atom_node.children[1])
            return ast.Repr(expr, atom_node.lineno, atom_node.column)
        else:
            raise AssertionError("unknown atom")

    def handle_testlist_gexp(self, gexp_node):
        if len(gexp_node.children) > 1 and \
                gexp_node.children[1].type == syms.comp_for:
            return self.handle_genexp(gexp_node)
        return self.handle_testlist(gexp_node)

    def count_comp_fors(self, comp_node, for_type, if_type):
        count = 0
        current_for = comp_node
        while True:
            count += 1
            if len(current_for.children) == 5:
                current_iter = current_for.children[4]
            else:
                return count
            while True:
                first_child = current_iter.children[0]
                if first_child.type == for_type:
                    current_for = current_iter.children[0]
                    break
                elif first_child.type == if_type:
                    if len(first_child.children) == 3:
                        current_iter = first_child.children[2]
                    else:
                        return count
                else:
                    raise AssertionError("should not reach here")

    def count_comp_ifs(self, iter_node, for_type):
        count = 0
        while True:
            first_child = iter_node.children[0]
            if first_child.type == for_type:
                return count
            count += 1
            if len(first_child.children) == 2:
                return count
            iter_node = first_child.children[2]

    @specialize.arg(2)
    def comprehension_helper(self, comp_node,
                             handle_source_expr_meth="handle_expr",
                             for_type=syms.comp_for, if_type=syms.comp_if,
                             iter_type=syms.comp_iter,
                             comp_fix_unamed_tuple_location=False):
        handle_source_expression = getattr(self, handle_source_expr_meth)
        fors_count = self.count_comp_fors(comp_node, for_type, if_type)
        comps = []
        for i in range(fors_count):
            for_node = comp_node.children[1]
            for_targets = self.handle_exprlist(for_node, ast.Store)
            expr = handle_source_expression(comp_node.children[3])
            assert isinstance(expr, ast.expr)
            if len(for_node.children) == 1:
                comp = ast.comprehension(for_targets[0], expr, None)
            else:
                col = comp_node.column
                line = comp_node.lineno
                # Modified in python2.7, see http://bugs.python.org/issue6704
                if comp_fix_unamed_tuple_location:
                    expr_node = for_targets[0]
                    assert isinstance(expr_node, ast.expr)
                    col = expr_node.col_offset
                    line = expr_node.lineno
                target = ast.Tuple(for_targets, ast.Store, line, col)
                comp = ast.comprehension(target, expr, None)
            if len(comp_node.children) == 5:
                comp_node = comp_iter = comp_node.children[4]
                assert comp_iter.type == iter_type
                ifs_count = self.count_comp_ifs(comp_iter, for_type)
                if ifs_count:
                    ifs = []
                    for j in range(ifs_count):
                        comp_node = comp_if = comp_iter.children[0]
                        ifs.append(self.handle_expr(comp_if.children[1]))
                        if len(comp_if.children) == 3:
                            comp_node = comp_iter = comp_if.children[2]
                    comp.ifs = ifs
                if comp_node.type == iter_type:
                    comp_node = comp_node.children[0]
            assert isinstance(comp, ast.comprehension)
            comps.append(comp)
        return comps

    def handle_genexp(self, genexp_node):
        elt = self.handle_expr(genexp_node.children[0])
        comps = self.comprehension_helper(genexp_node.children[1],
                                          comp_fix_unamed_tuple_location=True)
        return ast.GeneratorExp(elt, comps, genexp_node.lineno,
                                genexp_node.column)

    def handle_listcomp(self, listcomp_node):
        elt = self.handle_expr(listcomp_node.children[0])
        comps = self.comprehension_helper(listcomp_node.children[1],
                                          "handle_testlist",
                                          syms.list_for, syms.list_if,
                                          syms.list_iter,
                                          comp_fix_unamed_tuple_location=True)
        return ast.ListComp(elt, comps, listcomp_node.lineno,
                            listcomp_node.column)

    def handle_setcomp(self, set_maker):
        elt = self.handle_expr(set_maker.children[0])
        comps = self.comprehension_helper(set_maker.children[1],
                                          comp_fix_unamed_tuple_location=True)
        return ast.SetComp(elt, comps, set_maker.lineno, set_maker.column)

    def handle_dictcomp(self, dict_maker):
        key = self.handle_expr(dict_maker.children[0])
        value = self.handle_expr(dict_maker.children[2])
        comps = self.comprehension_helper(dict_maker.children[3],
                                          comp_fix_unamed_tuple_location=True)
        return ast.DictComp(key, value, comps, dict_maker.lineno,
                            dict_maker.column)

    def handle_exprlist(self, exprlist, context):
        exprs = []
        for i in range(0, len(exprlist.children), 2):
            child = exprlist.children[i]
            expr = self.handle_expr(child)
            self.set_context(expr, context)
            exprs.append(expr)
        return exprs
