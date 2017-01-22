"""
Generate Python bytecode from a Abstract Syntax Tree.
"""

# NOTE TO READERS: All the ugly and "obvious" isinstance assertions here are to
# help the annotator.  To it, unfortunately, everything is not so obvious.  If
# you figure out a way to remove them, great, but try a translation first,
# please.
import struct

from pypy.interpreter.astcompiler import ast, assemble, symtable, consts, misc
from pypy.interpreter.astcompiler import optimize # For side effects
from pypy.interpreter.pyparser.error import SyntaxError
from pypy.tool import stdlib_opcode as ops

C_INT_MAX = (2 ** (struct.calcsize('i') * 8)) / 2 - 1

def compile_ast(space, module, info):
    """Generate a code object from AST."""
    symbols = symtable.SymtableBuilder(space, module, info)
    return TopLevelCodeGenerator(space, module, symbols, info).assemble()


name_ops_default = misc.dict_to_switch({
    ast.Load: ops.LOAD_NAME,
    ast.Store: ops.STORE_NAME,
    ast.Del: ops.DELETE_NAME
})

name_ops_fast = misc.dict_to_switch({
    ast.Load: ops.LOAD_FAST,
    ast.Store: ops.STORE_FAST,
    ast.Del: ops.DELETE_FAST
})

name_ops_deref = misc.dict_to_switch({
    ast.Load: ops.LOAD_DEREF,
    ast.Store: ops.STORE_DEREF,
    ast.Del: ops.DELETE_DEREF,
})

name_ops_global = misc.dict_to_switch({
    ast.Load: ops.LOAD_GLOBAL,
    ast.Store: ops.STORE_GLOBAL,
    ast.Del: ops.DELETE_GLOBAL
})


unary_operations = misc.dict_to_switch({
    ast.Invert: ops.UNARY_INVERT,
    ast.Not: ops.UNARY_NOT,
    ast.UAdd: ops.UNARY_POSITIVE,
    ast.USub: ops.UNARY_NEGATIVE
})

binary_operations = misc.dict_to_switch({
    ast.Add: ops.BINARY_ADD,
    ast.Sub: ops.BINARY_SUBTRACT,
    ast.Mult: ops.BINARY_MULTIPLY,
    ast.Div: ops.BINARY_TRUE_DIVIDE,
    ast.Mod: ops.BINARY_MODULO,
    ast.Pow: ops.BINARY_POWER,
    ast.LShift: ops.BINARY_LSHIFT,
    ast.RShift: ops.BINARY_RSHIFT,
    ast.BitOr: ops.BINARY_OR,
    ast.BitAnd: ops.BINARY_AND,
    ast.BitXor: ops.BINARY_XOR,
    ast.FloorDiv: ops.BINARY_FLOOR_DIVIDE,
    ast.MatMult: ops.BINARY_MATRIX_MULTIPLY
})

inplace_operations = misc.dict_to_switch({
    ast.Add: ops.INPLACE_ADD,
    ast.Sub: ops.INPLACE_SUBTRACT,
    ast.Mult: ops.INPLACE_MULTIPLY,
    ast.Div: ops.INPLACE_TRUE_DIVIDE,
    ast.Mod: ops.INPLACE_MODULO,
    ast.Pow: ops.INPLACE_POWER,
    ast.LShift: ops.INPLACE_LSHIFT,
    ast.RShift: ops.INPLACE_RSHIFT,
    ast.BitOr: ops.INPLACE_OR,
    ast.BitAnd: ops.INPLACE_AND,
    ast.BitXor: ops.INPLACE_XOR,
    ast.FloorDiv: ops.INPLACE_FLOOR_DIVIDE,
    ast.MatMult: ops.INPLACE_MATRIX_MULTIPLY
})

compare_operations = misc.dict_to_switch({
    ast.Eq: 2,
    ast.NotEq: 3,
    ast.Lt: 0,
    ast.LtE: 1,
    ast.Gt: 4,
    ast.GtE: 5,
    ast.In: 6,
    ast.NotIn: 7,
    ast.Is: 8,
    ast.IsNot: 9
})

subscr_operations = misc.dict_to_switch({
    ast.AugLoad: ops.BINARY_SUBSCR,
    ast.Load: ops.BINARY_SUBSCR,
    ast.AugStore: ops.STORE_SUBSCR,
    ast.Store: ops.STORE_SUBSCR,
    ast.Del: ops.DELETE_SUBSCR
})


class __extend__(ast.GeneratorExp):

    def build_container(self, codegen):
        pass

    def get_generators(self):
        return self.generators

    def accept_comp_iteration(self, codegen, index):
        self.elt.walkabout(codegen)
        codegen.emit_op(ops.YIELD_VALUE)
        codegen.emit_op(ops.POP_TOP)


class __extend__(ast.ListComp):

    def build_container(self, codegen):
        # XXX: this is suboptimal: if we use BUILD_LIST_FROM_ARG it's faster
        # because it preallocates the list; however, we cannot use it because
        # at this point we only have the iterator, not the original iterable
        # object
        codegen.emit_op_arg(ops.BUILD_LIST, 0)

    def get_generators(self):
        return self.generators

    def accept_comp_iteration(self, codegen, index):
        self.elt.walkabout(codegen)
        codegen.emit_op_arg(ops.LIST_APPEND, index + 1)


class __extend__(ast.SetComp):

    def build_container(self, codegen):
        codegen.emit_op_arg(ops.BUILD_SET, 0)

    def get_generators(self):
        return self.generators

    def accept_comp_iteration(self, codegen, index):
        self.elt.walkabout(codegen)
        codegen.emit_op_arg(ops.SET_ADD, index + 1)


class __extend__(ast.DictComp):

    def build_container(self, codegen):
        codegen.emit_op_arg(ops.BUILD_MAP, 0)

    def get_generators(self):
        return self.generators

    def accept_comp_iteration(self, codegen, index):
        self.value.walkabout(codegen)
        self.key.walkabout(codegen)
        codegen.emit_op_arg(ops.MAP_ADD, index + 1)


# These are frame blocks.
F_BLOCK_LOOP = 0
F_BLOCK_EXCEPT = 1
F_BLOCK_FINALLY = 2
F_BLOCK_FINALLY_END = 3


class PythonCodeGenerator(assemble.PythonCodeMaker):
    """Base code generator.

    A subclass of this is created for every scope to be compiled.  It walks
    across the AST tree generating bytecode as needed.
    """

    def __init__(self, space, name, tree, lineno, symbols, compile_info,
                 qualname):
        self.scope = symbols.find_scope(tree)
        assemble.PythonCodeMaker.__init__(self, space, name, lineno,
                                          self.scope, compile_info)
        self.symbols = symbols
        self.frame_blocks = []
        self.interactive = False
        self.temporary_name_counter = 1
        if isinstance(self.scope, symtable.FunctionScope):
            self.qualname = qualname + '.<locals>'
        else:
            self.qualname = qualname
        self._compile(tree)

    def _compile(self, tree):
        """Override in subclasses to compile a scope."""
        raise NotImplementedError

    def current_temporary_name(self):
        """Return the name of the current temporary variable.

        This must be in sync with the one during symbol table building.
        """
        name = "_[%d]" % (self.temporary_name_counter,)
        self.temporary_name_counter += 1
        assert self.scope.lookup(name) != symtable.SCOPE_UNKNOWN
        return name

    def sub_scope(self, kind, name, node, lineno):
        """Convenience function for compiling a sub scope."""
        if self.scope.lookup(name) == symtable.SCOPE_GLOBAL_EXPLICIT:
            qualname = name
        elif self.qualname:
            qualname = '%s.%s' % (self.qualname, name)
        else:
            qualname = name
        generator = kind(self.space, name, node, lineno, self.symbols,
                         self.compile_info, qualname)
        return generator.assemble(), qualname

    def push_frame_block(self, kind, block):
        self.frame_blocks.append((kind, block))

    def pop_frame_block(self, kind, block):
        actual_kind, old_block = self.frame_blocks.pop()
        assert actual_kind == kind and old_block is block, \
            "mismatched frame blocks"

    def error(self, msg, node):
        raise SyntaxError(msg, node.lineno, node.col_offset,
                          filename=self.compile_info.filename)

    def name_op(self, identifier, ctx):
        """Generate an operation appropriate for the scope of the identifier."""
        scope = self.scope.lookup(identifier)
        op = ops.NOP
        container = self.names
        if scope == symtable.SCOPE_LOCAL:
            if self.scope.can_be_optimized:
                container = self.var_names
                op = name_ops_fast(ctx)
        elif scope == symtable.SCOPE_FREE:
            op = name_ops_deref(ctx)
            if op == ops.LOAD_DEREF and isinstance(self, ClassCodeGenerator):
                op = ops.LOAD_CLASSDEREF
            container = self.free_vars
        elif scope == symtable.SCOPE_CELL:
            op = name_ops_deref(ctx)
            container = self.cell_vars
        elif scope == symtable.SCOPE_GLOBAL_IMPLICIT:
            if self.scope.optimized:
                op = name_ops_global(ctx)
        elif scope == symtable.SCOPE_GLOBAL_EXPLICIT:
            op = name_ops_global(ctx)
        if op == ops.NOP:
            op = name_ops_default(ctx)
        self.emit_op_arg(op, self.add_name(container, identifier))

    def possible_docstring(self, node):
        if isinstance(node, ast.Expr) and self.compile_info.optimize < 2:
            expr_value = node.value
            if isinstance(expr_value, ast.Str):
                return expr_value
        return None

    def ensure_docstring_constant(self, body):
        # If there's a docstring, store it as the first constant.
        if body:
            doc_expr = self.possible_docstring(body[0])
        else:
            doc_expr = None
        if doc_expr is not None:
            self.add_const(doc_expr.s)
            self.scope.doc_removable = True
            return True
        else:
            self.add_const(self.space.w_None)
            return False

    def _get_code_flags(self):
        return 0

    def _handle_body(self, body):
        """Compile a list of statements, handling doc strings if needed."""
        if body:
            start = 0
            doc_expr = self.possible_docstring(body[0])
            if doc_expr is not None:
                start = 1
                doc_expr.walkabout(self)
                self.name_op("__doc__", ast.Store)
                self.scope.doc_removable = True
            for i in range(start, len(body)):
                body[i].walkabout(self)
            return True
        else:
            return False

    def visit_Module(self, mod):
        if not self._handle_body(mod.body):
            self.first_lineno = self.lineno = 1

    def visit_Interactive(self, mod):
        self.interactive = True
        self.visit_sequence(mod.body)

    def visit_Expression(self, mod):
        self.add_none_to_final_return = False
        mod.body.walkabout(self)

    def _make_function(self, code, num_defaults=0, qualname=None):
        """Emit the opcodes to turn a code object into a function."""
        w_qualname = self.space.wrap((qualname or code.co_name).decode('utf-8'))
        if code.co_freevars:
            # Load cell and free vars to pass on.
            for free in code.co_freevars:
                free_scope = self.scope.lookup(free)
                if free_scope in (symtable.SCOPE_CELL,
                                  symtable.SCOPE_CELL_CLASS):
                    index = self.cell_vars[free]
                else:
                    index = self.free_vars[free]
                self.emit_op_arg(ops.LOAD_CLOSURE, index)
            self.emit_op_arg(ops.BUILD_TUPLE, len(code.co_freevars))
            self.load_const(code)
            self.load_const(w_qualname)
            self.emit_op_arg(ops.MAKE_CLOSURE, num_defaults)
        else:
            self.load_const(code)
            self.load_const(w_qualname)
            self.emit_op_arg(ops.MAKE_FUNCTION, num_defaults)

    def _visit_kwonlydefaults(self, args):
        defaults = 0
        for i, default in enumerate(args.kw_defaults):
            if default:
                kwonly = args.kwonlyargs[i]
                mangled = self.scope.mangle(kwonly.arg).decode('utf-8')
                self.load_const(self.space.wrap(mangled))
                default.walkabout(self)
                defaults += 1
        return defaults

    def _visit_arg_annotation(self, name, ann, names):
        if ann:
            ann.walkabout(self)
            names.append(self.scope.mangle(name))

    def _visit_arg_annotations(self, args, names):
        if args:
            for arg in args:
                self._visit_arg_annotation(arg.arg, arg.annotation, names)

    def _visit_annotations(self, func, args, returns):
        space = self.space
        names = []
        self._visit_arg_annotations(args.args, names)
        if args.vararg:
            self._visit_arg_annotation(args.vararg.arg, args.vararg.annotation,
                                       names)
        self._visit_arg_annotations(args.kwonlyargs, names)
        if args.kwarg:
            self._visit_arg_annotation(args.kwarg.arg, args.kwarg.annotation,
                                       names)
        self._visit_arg_annotation("return", returns, names)
        l = len(names)
        if l:
            if l > 65534:
                self.error("too many annotations", func)
            w_tup = space.newtuple([space.wrap(name.decode('utf-8'))
                                    for name in names])
            self.load_const(w_tup)
            l += 1
        return l

    def _visit_function(self, func, function_code_generator):
        self.update_position(func.lineno, True)
        # Load decorators first, but apply them after the function is created.
        self.visit_sequence(func.decorator_list)
        args = func.args
        assert isinstance(args, ast.arguments)
        self.visit_sequence(args.defaults)
        kw_default_count = 0
        if args.kwonlyargs:
            kw_default_count = self._visit_kwonlydefaults(args)
        num_annotations = self._visit_annotations(func, args, func.returns)
        num_defaults = len(args.defaults) if args.defaults is not None else 0
        oparg = num_defaults
        oparg |= kw_default_count << 8
        oparg |= num_annotations << 16
        code, qualname = self.sub_scope(function_code_generator, func.name,
                                        func, func.lineno)
        self._make_function(code, oparg, qualname=qualname)
        # Apply decorators.
        if func.decorator_list:
            for i in range(len(func.decorator_list)):
                self.emit_op_arg(ops.CALL_FUNCTION, 1)
        self.name_op(func.name, ast.Store)

    def visit_FunctionDef(self, func):
        self._visit_function(func, FunctionCodeGenerator)

    def visit_AsyncFunctionDef(self, func):
        self._visit_function(func, AsyncFunctionCodeGenerator)

    def visit_Lambda(self, lam):
        self.update_position(lam.lineno)
        args = lam.args
        assert isinstance(args, ast.arguments)
        self.visit_sequence(args.defaults)
        kw_default_count = 0
        if args.kwonlyargs:
            kw_default_count = self._visit_kwonlydefaults(args)
        default_count = len(args.defaults) if args.defaults is not None else 0
        code, qualname = self.sub_scope(
            LambdaCodeGenerator, "<lambda>", lam, lam.lineno)
        oparg = default_count
        oparg |= kw_default_count << 8
        self._make_function(code, oparg, qualname=qualname)

    def visit_ClassDef(self, cls):
        self.update_position(cls.lineno, True)
        self.visit_sequence(cls.decorator_list)
        # 1. compile the class body into a code object
        code, qualname = self.sub_scope(
            ClassCodeGenerator, cls.name, cls, cls.lineno)
        # 2. load the 'build_class' function
        self.emit_op(ops.LOAD_BUILD_CLASS)
        # 3. load a function (or closure) made from the code object
        self._make_function(code, qualname=qualname)
        # 4. load class name
        self.load_const(self.space.wrap(cls.name.decode('utf-8')))
        # 5. generate the rest of the code for the call
        self._make_call(2, cls.bases, cls.keywords)
        # 6. apply decorators
        if cls.decorator_list:
            for i in range(len(cls.decorator_list)):
                self.emit_op_arg(ops.CALL_FUNCTION, 1)
        # 7. store into <name>
        self.name_op(cls.name, ast.Store)

    def _op_for_augassign(self, op):
        return inplace_operations(op)

    def visit_AugAssign(self, assign):
        self.update_position(assign.lineno, True)
        target = assign.target
        if isinstance(target, ast.Attribute):
            attr = ast.Attribute(target.value, target.attr, ast.AugLoad,
                                 target.lineno, target.col_offset)
            attr.walkabout(self)
            assign.value.walkabout(self)
            self.emit_op(self._op_for_augassign(assign.op))
            attr.ctx = ast.AugStore
            attr.walkabout(self)
        elif isinstance(target, ast.Subscript):
            sub = ast.Subscript(target.value, target.slice, ast.AugLoad,
                                target.lineno, target.col_offset)
            sub.walkabout(self)
            assign.value.walkabout(self)
            self.emit_op(self._op_for_augassign(assign.op))
            sub.ctx = ast.AugStore
            sub.walkabout(self)
        elif isinstance(target, ast.Name):
            self.name_op(target.id, ast.Load)
            assign.value.walkabout(self)
            self.emit_op(self._op_for_augassign(assign.op))
            self.name_op(target.id, ast.Store)
        else:
            self.error("illegal expression for augmented assignment", assign)

    def visit_Assert(self, asrt):
        if self.compile_info.optimize >= 1:
            return
        self.update_position(asrt.lineno)
        end = self.new_block()
        if self.compile_info.optimize != 0:
            self.emit_jump(ops.JUMP_IF_NOT_DEBUG, end)
        asrt.test.accept_jump_if(self, True, end)
        self.emit_op_name(ops.LOAD_GLOBAL, self.names, "AssertionError")
        if asrt.msg:
            asrt.msg.walkabout(self)
            self.emit_op_arg(ops.CALL_FUNCTION, 1)
        self.emit_op_arg(ops.RAISE_VARARGS, 1)
        self.use_next_block(end)

    def _binop(self, op):
        return binary_operations(op)

    def visit_BinOp(self, binop):
        self.update_position(binop.lineno)
        binop.left.walkabout(self)
        binop.right.walkabout(self)
        self.emit_op(self._binop(binop.op))

    def visit_Return(self, ret):
        self.update_position(ret.lineno, True)
        if ret.value:
            ret.value.walkabout(self)
        else:
            self.load_const(self.space.w_None)
        self.emit_op(ops.RETURN_VALUE)

    def visit_Delete(self, delete):
        self.update_position(delete.lineno, True)
        self.visit_sequence(delete.targets)

    def visit_If(self, if_):
        self.update_position(if_.lineno, True)
        end = self.new_block()
        test_constant = if_.test.as_constant_truth(self.space)
        if test_constant == optimize.CONST_FALSE:
            self.visit_sequence(if_.orelse)
        elif test_constant == optimize.CONST_TRUE:
            self.visit_sequence(if_.body)
        else:
            if if_.orelse:
                otherwise = self.new_block()
            else:
                otherwise = end
            if_.test.accept_jump_if(self, False, otherwise)
            self.visit_sequence(if_.body)
            self.emit_jump(ops.JUMP_FORWARD, end)
            if if_.orelse:
                self.use_next_block(otherwise)
                self.visit_sequence(if_.orelse)
        self.use_next_block(end)

    def visit_Break(self, br):
        self.update_position(br.lineno, True)
        for f_block in self.frame_blocks:
            if f_block[0] == F_BLOCK_LOOP:
                break
        else:
            self.error("'break' outside loop", br)
        self.emit_op(ops.BREAK_LOOP)

    def visit_Continue(self, cont):
        self.update_position(cont.lineno, True)
        if not self.frame_blocks:
            self.error("'continue' not properly in loop", cont)
        current_block, block = self.frame_blocks[-1]
        # Continue cannot be in a finally block.
        if current_block == F_BLOCK_LOOP:
            self.emit_jump(ops.JUMP_ABSOLUTE, block, True)
        elif current_block == F_BLOCK_EXCEPT or \
                current_block == F_BLOCK_FINALLY:
            for i in range(len(self.frame_blocks) - 2, -1, -1):
                f_type, block = self.frame_blocks[i]
                if f_type == F_BLOCK_LOOP:
                    self.emit_jump(ops.CONTINUE_LOOP, block, True)
                    break
                if f_type == F_BLOCK_FINALLY_END:
                    self.error("'continue' not supported inside 'finally' "
                                   "clause", cont)
            else:
                self.error("'continue' not properly in loop", cont)
        elif current_block == F_BLOCK_FINALLY_END:
            self.error("'continue' not supported inside 'finally' clause", cont)

    def visit_For(self, fr):
        self.update_position(fr.lineno, True)
        start = self.new_block()
        cleanup = self.new_block()
        end = self.new_block()
        self.emit_jump(ops.SETUP_LOOP, end)
        self.push_frame_block(F_BLOCK_LOOP, start)
        fr.iter.walkabout(self)
        self.emit_op(ops.GET_ITER)
        self.use_next_block(start)
        # This adds another line, so each for iteration can be traced.
        self.lineno_set = False
        self.emit_jump(ops.FOR_ITER, cleanup)
        fr.target.walkabout(self)
        self.visit_sequence(fr.body)
        self.emit_jump(ops.JUMP_ABSOLUTE, start, True)
        self.use_next_block(cleanup)
        self.emit_op(ops.POP_BLOCK)
        self.pop_frame_block(F_BLOCK_LOOP, start)
        self.visit_sequence(fr.orelse)
        self.use_next_block(end)

    def visit_AsyncFor(self, fr):
        self.update_position(fr.lineno, True)
        b_try = self.new_block()
        b_except = self.new_block()
        b_end = self.new_block()
        b_after_try = self.new_block()
        b_try_cleanup = self.new_block()
        b_after_loop = self.new_block()
        b_after_loop_else = self.new_block()

        self.emit_jump(ops.SETUP_LOOP, b_after_loop)
        self.push_frame_block(F_BLOCK_LOOP, b_try)

        fr.iter.walkabout(self)
        self.emit_op(ops.GET_AITER)
        self.load_const(self.space.w_None)
        self.emit_op(ops.YIELD_FROM)

        self.use_next_block(b_try)
        # This adds another line, so each for iteration can be traced.
        self.lineno_set = False
        self.emit_jump(ops.SETUP_EXCEPT, b_except)
        self.push_frame_block(F_BLOCK_EXCEPT, b_try)

        self.emit_op(ops.GET_ANEXT)
        self.load_const(self.space.w_None)
        self.emit_op(ops.YIELD_FROM)
        fr.target.walkabout(self)
        self.emit_op(ops.POP_BLOCK)
        self.pop_frame_block(F_BLOCK_EXCEPT, b_try)
        self.emit_jump(ops.JUMP_FORWARD, b_after_try)

        self.use_next_block(b_except)
        self.emit_op(ops.DUP_TOP)
        self.emit_op_name(ops.LOAD_GLOBAL, self.names, "StopAsyncIteration")
        self.emit_op_arg(ops.COMPARE_OP, 10)
        self.emit_jump(ops.POP_JUMP_IF_FALSE, b_try_cleanup, True)

        self.emit_op(ops.POP_TOP)
        self.emit_op(ops.POP_TOP)
        self.emit_op(ops.POP_TOP)
        self.emit_op(ops.POP_EXCEPT) # for SETUP_EXCEPT
        # Manually remove the 'aiter' object from the valuestack.
        # This POP_TOP is not needed from the point of view of
        # pyopcode.py, which will pop anything to match the stack
        # depth of the SETUP_LOOP, but it is needed to make
        # PythonCodeMaker._stacksize() compute an exact result and not
        # crash with StackDepthComputationError.
        self.emit_op(ops.POP_TOP)
        self.emit_op(ops.POP_BLOCK) # for SETUP_LOOP
        self.emit_jump(ops.JUMP_ABSOLUTE, b_after_loop_else, True)

        self.use_next_block(b_try_cleanup)
        self.emit_op(ops.END_FINALLY)

        self.use_next_block(b_after_try)
        self.visit_sequence(fr.body)
        self.emit_jump(ops.JUMP_ABSOLUTE, b_try, True)

        self.emit_op(ops.POP_BLOCK) # for SETUP_LOOP
        self.pop_frame_block(F_BLOCK_LOOP, b_try)

        self.use_next_block(b_after_loop)
        self.emit_jump(ops.JUMP_ABSOLUTE, b_end, True)

        self.use_next_block(b_after_loop_else)
        self.visit_sequence(fr.orelse)

        self.use_next_block(b_end)

    def visit_While(self, wh):
        self.update_position(wh.lineno, True)
        test_constant = wh.test.as_constant_truth(self.space)
        if test_constant == optimize.CONST_FALSE:
            self.visit_sequence(wh.orelse)
        else:
            end = self.new_block()
            anchor = None
            if test_constant == optimize.CONST_NOT_CONST:
                anchor = self.new_block()
            self.emit_jump(ops.SETUP_LOOP, end)
            loop = self.new_block()
            self.push_frame_block(F_BLOCK_LOOP, loop)
            self.use_next_block(loop)
            if test_constant == optimize.CONST_NOT_CONST:
                # Force another lineno to be set for tracing purposes.
                self.lineno_set = False
                wh.test.accept_jump_if(self, False, anchor)
            self.visit_sequence(wh.body)
            self.emit_jump(ops.JUMP_ABSOLUTE, loop, True)
            if test_constant == optimize.CONST_NOT_CONST:
                self.use_next_block(anchor)
            self.emit_op(ops.POP_BLOCK)
            self.pop_frame_block(F_BLOCK_LOOP, loop)
            self.visit_sequence(wh.orelse)
            self.use_next_block(end)

    def _visit_try_except(self, tr):
        self.update_position(tr.lineno, True)
        exc = self.new_block()
        otherwise = self.new_block()
        end = self.new_block()
        self.emit_jump(ops.SETUP_EXCEPT, exc)
        body = self.use_next_block()
        self.push_frame_block(F_BLOCK_EXCEPT, body)
        self.visit_sequence(tr.body)
        self.emit_op(ops.POP_BLOCK)
        self.pop_frame_block(F_BLOCK_EXCEPT, body)
        self.emit_jump(ops.JUMP_FORWARD, otherwise)
        self.use_next_block(exc)
        for handler in tr.handlers:
            assert isinstance(handler, ast.ExceptHandler)
            self.update_position(handler.lineno, True)
            next_except = self.new_block()
            if handler.type:
                self.emit_op(ops.DUP_TOP)
                handler.type.walkabout(self)
                self.emit_op_arg(ops.COMPARE_OP, 10)
                self.emit_jump(ops.POP_JUMP_IF_FALSE, next_except, True)
            self.emit_op(ops.POP_TOP)
            if handler.name:
                ## generate the equivalent of:
                ##
                ## try:
                ##     # body
                ## except type as name:
                ##     try:
                ##         # body
                ##     finally:
                ##         name = None
                ##         del name
                #
                cleanup_end = self.new_block()
                self.name_op(handler.name, ast.Store)
                self.emit_op(ops.POP_TOP)
                # second try
                self.emit_jump(ops.SETUP_FINALLY, cleanup_end)
                cleanup_body = self.use_next_block()
                self.push_frame_block(F_BLOCK_FINALLY, cleanup_body)
                # second # body
                self.visit_sequence(handler.body)
                self.emit_op(ops.POP_BLOCK)
                self.pop_frame_block(F_BLOCK_FINALLY, cleanup_body)
                # finally
                self.load_const(self.space.w_None)
                self.use_next_block(cleanup_end)
                self.push_frame_block(F_BLOCK_FINALLY_END, cleanup_end)
                # name = None
                self.load_const(self.space.w_None)
                self.name_op(handler.name, ast.Store)
                # del name
                self.name_op(handler.name, ast.Del)
                #
                self.emit_op(ops.END_FINALLY)
                self.pop_frame_block(F_BLOCK_FINALLY_END, cleanup_end)
            else:
                self.emit_op(ops.POP_TOP)
                self.emit_op(ops.POP_TOP)
                cleanup_body = self.use_next_block()
                self.push_frame_block(F_BLOCK_FINALLY, cleanup_body)
                self.visit_sequence(handler.body)
                self.pop_frame_block(F_BLOCK_FINALLY, cleanup_body)
            #
            self.emit_op(ops.POP_EXCEPT)
            self.emit_jump(ops.JUMP_FORWARD, end)
            self.use_next_block(next_except)
        self.emit_op(ops.END_FINALLY)   # this END_FINALLY will always re-raise
        self.use_next_block(otherwise)
        self.visit_sequence(tr.orelse)
        self.use_next_block(end)

    def _visit_try_finally(self, tr):
        self.update_position(tr.lineno, True)
        end = self.new_block()
        self.emit_jump(ops.SETUP_FINALLY, end)
        body = self.use_next_block()
        self.push_frame_block(F_BLOCK_FINALLY, body)
        if tr.handlers:
            self._visit_try_except(tr)
        else:
            self.visit_sequence(tr.body)
        self.emit_op(ops.POP_BLOCK)
        self.pop_frame_block(F_BLOCK_FINALLY, body)
        # Indicates there was no exception.
        self.load_const(self.space.w_None)
        self.use_next_block(end)
        self.push_frame_block(F_BLOCK_FINALLY_END, end)
        self.visit_sequence(tr.finalbody)
        self.emit_op(ops.END_FINALLY)
        self.pop_frame_block(F_BLOCK_FINALLY_END, end)

    def visit_Try(self, tr):
        if tr.finalbody:
            return self._visit_try_finally(tr)
        else:
            return self._visit_try_except(tr)

    def _import_as(self, alias):
        source_name = alias.name
        dot = source_name.find(".")
        if dot > 0:
            while True:
                start = dot + 1
                dot = source_name.find(".", start)
                if dot < 0:
                    end = len(source_name)
                else:
                    end = dot
                attr = source_name[start:end]
                self.emit_op_name(ops.LOAD_ATTR, self.names, attr)
                if dot < 0:
                    break
        self.name_op(alias.asname, ast.Store)

    def visit_Import(self, imp):
        self.update_position(imp.lineno, True)
        for alias in imp.names:
            assert isinstance(alias, ast.alias)
            level = 0
            self.load_const(self.space.wrap(level))
            self.load_const(self.space.w_None)
            self.emit_op_name(ops.IMPORT_NAME, self.names, alias.name)
            # If there's no asname then we store the root module.  If there is
            # an asname, _import_as stores the last module of the chain into it.
            if alias.asname:
                self._import_as(alias)
            else:
                dot = alias.name.find(".")
                if dot < 0:
                    store_name = alias.name
                else:
                    store_name = alias.name[:dot]
                self.name_op(store_name, ast.Store)

    def visit_ImportFrom(self, imp):
        self.update_position(imp.lineno, True)
        space = self.space
        first = imp.names[0]
        assert isinstance(first, ast.alias)
        star_import = len(imp.names) == 1 and first.name == "*"
        # Various error checking for future imports.
        if imp.module == "__future__":
            last_line, last_offset = self.compile_info.last_future_import
            if imp.lineno > last_line or \
                    imp.lineno == last_line and imp.col_offset > last_offset:
                self.error("__future__ statements must appear at beginning "
                               "of file", imp)
            if star_import:
                self.error("* not valid in __future__ imports", imp)
            compiler = space.createcompiler()
            for alias in imp.names:
                assert isinstance(alias, ast.alias)
                if alias.name not in compiler.future_flags.compiler_features:
                    if alias.name == "braces":
                        self.error("not a chance", imp)
                    self.error("future feature %s is not defined" %
                               (alias.name,), imp)
        self.load_const(space.wrap(imp.level))
        names_w = [None]*len(imp.names)
        for i in range(len(imp.names)):
            alias = imp.names[i]
            assert isinstance(alias, ast.alias)
            names_w[i] = space.wrap(alias.name.decode('utf-8'))
        self.load_const(space.newtuple(names_w))
        if imp.module:
            mod_name = imp.module
        else:
            # In the case of a relative import.
            mod_name = ""
        self.emit_op_name(ops.IMPORT_NAME, self.names, mod_name)
        if star_import:
            self.emit_op(ops.IMPORT_STAR)
        else:
            for alias in imp.names:
                assert isinstance(alias, ast.alias)
                self.emit_op_name(ops.IMPORT_FROM, self.names, alias.name)
                if alias.asname:
                    store_name = alias.asname
                else:
                    store_name = alias.name
                self.name_op(store_name, ast.Store)
            self.emit_op(ops.POP_TOP)

    def visit_Assign(self, assign):
        self.update_position(assign.lineno, True)
        if self._optimize_unpacking(assign):
            return
        assign.value.walkabout(self)
        duplications = len(assign.targets) - 1
        for i in range(len(assign.targets)):
            if i < duplications:
                self.emit_op(ops.DUP_TOP)
            assign.targets[i].walkabout(self)

    def _optimize_unpacking(self, assign):
        """Try to optimize out BUILD_TUPLE and UNPACK_SEQUENCE opcodes."""
        if len(assign.targets) != 1:
            return False
        targets = assign.targets[0].as_node_list(self.space)
        if targets is None:
            return False
        values = assign.value.as_node_list(self.space)
        if values is None:
            return False
        targets_count = len(targets)
        values_count = len(values)
        if targets_count != values_count:
            return False
        for target in targets:
            if not isinstance(target, ast.Name):
                if isinstance(target, ast.Starred):
                    # these require extra checks
                    return False
                break
        else:
            self.visit_sequence(values)
            seen_names = {}
            for i in range(targets_count - 1, -1, -1):
                target = targets[i]
                assert isinstance(target, ast.Name)
                if target.id not in seen_names:
                    seen_names[target.id] = True
                    self.name_op(target.id, ast.Store)
                else:
                    self.emit_op(ops.POP_TOP)
            return True
        if values_count > 3:
            return False
        self.visit_sequence(values)
        if values_count == 2:
            self.emit_op(ops.ROT_TWO)
        elif values_count == 3:
            self.emit_op(ops.ROT_THREE)
            self.emit_op(ops.ROT_TWO)
        self.visit_sequence(targets)
        return True

    def visit_With(self, wih):
        self.update_position(wih.lineno, True)
        self.handle_withitem(wih, 0, is_async=False)

    def handle_withitem(self, wih, pos, is_async):
        body_block = self.new_block()
        cleanup = self.new_block()
        witem = wih.items[pos]
        witem.context_expr.walkabout(self)
        if not is_async:
            self.emit_jump(ops.SETUP_WITH, cleanup)
        else:
            self.emit_op(ops.BEFORE_ASYNC_WITH)
            self.emit_op(ops.GET_AWAITABLE)
            self.load_const(self.space.w_None)
            self.emit_op(ops.YIELD_FROM)
            self.emit_jump(ops.SETUP_ASYNC_WITH, cleanup)

        self.use_next_block(body_block)
        self.push_frame_block(F_BLOCK_FINALLY, body_block)
        if witem.optional_vars:
            witem.optional_vars.walkabout(self)
        else:
            self.emit_op(ops.POP_TOP)
        if pos == len(wih.items) - 1:
            self.visit_sequence(wih.body)
        else:
            self.handle_withitem(wih, pos + 1, is_async=is_async)
        self.emit_op(ops.POP_BLOCK)
        self.pop_frame_block(F_BLOCK_FINALLY, body_block)
        self.load_const(self.space.w_None)
        self.use_next_block(cleanup)
        self.push_frame_block(F_BLOCK_FINALLY_END, cleanup)
        self.emit_op(ops.WITH_CLEANUP_START)
        if is_async:
            self.emit_op(ops.GET_AWAITABLE)
            self.load_const(self.space.w_None)
            self.emit_op(ops.YIELD_FROM)
        self.emit_op(ops.WITH_CLEANUP_FINISH)
        self.emit_op(ops.END_FINALLY)
        self.pop_frame_block(F_BLOCK_FINALLY_END, cleanup)

    def visit_AsyncWith(self, wih):
        self.update_position(wih.lineno, True)
        self.handle_withitem(wih, 0, is_async=True)

    def visit_Raise(self, rais):
        self.update_position(rais.lineno, True)
        arg = 0
        if rais.exc:
            rais.exc.walkabout(self)
            arg += 1
            if rais.cause:
                rais.cause.walkabout(self)
                arg += 1
        self.emit_op_arg(ops.RAISE_VARARGS, arg)

    def visit_Global(self, glob):
        # Handled in symbol table building.
        pass

    def visit_Nonlocal(self, glob):
        # Handled in symbol table building.
        pass

    def visit_Pass(self, pas):
        self.update_position(pas.lineno, True)

    def visit_Expr(self, expr):
        self.update_position(expr.lineno, True)
        if self.interactive:
            expr.value.walkabout(self)
            self.emit_op(ops.PRINT_EXPR)
        elif not (isinstance(expr.value, ast.Num) or
                  isinstance(expr.value, ast.Str)):
            expr.value.walkabout(self)
            self.emit_op(ops.POP_TOP)

    def visit_Yield(self, yie):
        self.update_position(yie.lineno)
        if yie.value:
            yie.value.walkabout(self)
        else:
            self.load_const(self.space.w_None)
        self.emit_op(ops.YIELD_VALUE)

    def visit_YieldFrom(self, yfr):
        self.update_position(yfr.lineno)
        yfr.value.walkabout(self)
        self.emit_op(ops.GET_YIELD_FROM_ITER)
        self.load_const(self.space.w_None)
        self.emit_op(ops.YIELD_FROM)

    def visit_Await(self, aw):
        self.update_position(aw.lineno)
        aw.value.walkabout(self)
        self.emit_op(ops.GET_AWAITABLE)
        self.load_const(self.space.w_None)
        self.emit_op(ops.YIELD_FROM)

    def visit_Num(self, num):
        self.update_position(num.lineno)
        self.load_const(num.n)

    def visit_Str(self, string):
        self.update_position(string.lineno)
        self.load_const(string.s)

    def visit_Bytes(self, b):
        self.update_position(b.lineno)
        self.load_const(b.s)

    def visit_Const(self, const):
        self.update_position(const.lineno)
        self.load_const(const.obj)

    def visit_Ellipsis(self, e):
        self.load_const(self.space.w_Ellipsis)

    def visit_UnaryOp(self, op):
        self.update_position(op.lineno)
        op.operand.walkabout(self)
        self.emit_op(unary_operations(op.op))

    def visit_BoolOp(self, op):
        self.update_position(op.lineno)
        if op.op == ast.And:
            instr = ops.JUMP_IF_FALSE_OR_POP
        else:
            instr = ops.JUMP_IF_TRUE_OR_POP
        end = self.new_block()
        for value in op.values[:-1]:
            value.walkabout(self)
            self.emit_jump(instr, end, True)
        op.values[-1].walkabout(self)
        self.use_next_block(end)

    def visit_Compare(self, comp):
        self.update_position(comp.lineno)
        comp.left.walkabout(self)
        ops_count = len(comp.ops)
        cleanup = None
        if ops_count > 1:
            cleanup = self.new_block()
            comp.comparators[0].walkabout(self)
        for i in range(1, ops_count):
            self.emit_op(ops.DUP_TOP)
            self.emit_op(ops.ROT_THREE)
            op_kind = compare_operations(comp.ops[i - 1])
            self.emit_op_arg(ops.COMPARE_OP, op_kind)
            self.emit_jump(ops.JUMP_IF_FALSE_OR_POP, cleanup, True)
            if i < (ops_count - 1):
                comp.comparators[i].walkabout(self)
        last_op, last_comparator = comp.ops[-1], comp.comparators[-1]
        if not self._optimize_comparator(last_op, last_comparator):
            last_comparator.walkabout(self)
        self.emit_op_arg(ops.COMPARE_OP, compare_operations(last_op))
        if ops_count > 1:
            end = self.new_block()
            self.emit_jump(ops.JUMP_FORWARD, end)
            self.use_next_block(cleanup)
            self.emit_op(ops.ROT_TWO)
            self.emit_op(ops.POP_TOP)
            self.use_next_block(end)

    def _optimize_comparator(self, op, node):
        """Fold lists/sets of constants in the context of "in"/"not in".

        lists are folded into tuples, sets into frozensets, otherwise
        returns False
        """
        if op in (ast.In, ast.NotIn):
            is_list = isinstance(node, ast.List)
            if is_list or isinstance(node, ast.Set):
                w_const = self._tuple_of_consts(node.elts)
                if w_const is not None:
                    if not is_list:
                        from pypy.objspace.std.setobject import (
                            W_FrozensetObject)
                        w_const = W_FrozensetObject(self.space, w_const)
                    self.load_const(w_const)
                    return True
        return False

    def _tuple_of_consts(self, elts):
        """Return a tuple of consts from elts if possible, or None"""
        count = len(elts) if elts is not None else 0
        consts_w = [None] * count
        for i in range(count):
            w_value = elts[i].as_constant()
            if w_value is None:
                # Not all constants
                return None
            consts_w[i] = w_value
        return self.space.newtuple(consts_w)

    def visit_IfExp(self, ifexp):
        self.update_position(ifexp.lineno)
        end = self.new_block()
        otherwise = self.new_block()
        ifexp.test.accept_jump_if(self, False, otherwise)
        ifexp.body.walkabout(self)
        self.emit_jump(ops.JUMP_FORWARD, end)
        self.use_next_block(otherwise)
        ifexp.orelse.walkabout(self)
        self.use_next_block(end)

    def _visit_starunpack(self, node, elts, single_op, inner_op, outer_op):
        elt_count = len(elts) if elts else 0
        seen_star = 0
        elt_subitems = 0
        for i in range(elt_count):
            elt = elts[i]
            is_starred = isinstance(elt, ast.Starred)
            if is_starred:
                if seen_star:
                    self.emit_op_arg(inner_op, seen_star)
                    seen_star = 0
                    elt_subitems += 1
                elt.value.walkabout(self)
                elt_subitems += 1
            else:
                elt.walkabout(self)
                seen_star += 1
        if elt_subitems:
            if seen_star:
                self.emit_op_arg(inner_op, seen_star)
                elt_subitems += 1
            self.emit_op_arg(outer_op, elt_subitems)
        else:
            self.emit_op_arg(single_op, seen_star)

    def _visit_assignment(self, node, elts, ctx):
        elt_count = len(elts) if elts else 0
        if ctx == ast.Store:
            seen_star = False
            for i in range(elt_count):
                elt = elts[i]
                is_starred = isinstance(elt, ast.Starred)
                if is_starred and not seen_star:
                    if i >= 1 << 8 or elt_count - i - 1 >= (C_INT_MAX >> 8):
                        self.error("too many expressions in star-unpacking "
                                   "assignment", node)
                    self.emit_op_arg(ops.UNPACK_EX,
                                     i + ((elt_count - i - 1) << 8))
                    seen_star = True
                    elts[i] = elt.value
                elif is_starred:
                    self.error("two starred expressions in assignment", node)
            if not seen_star:
                self.emit_op_arg(ops.UNPACK_SEQUENCE, elt_count)
        self.visit_sequence(elts)

    def visit_Starred(self, star):
        if star.ctx != ast.Store:
            self.error("can't use starred expression here",
                       star)
        self.error("starred assignment target must be in a list or tuple", star)

    def visit_Tuple(self, tup):
        self.update_position(tup.lineno)
        if tup.ctx == ast.Store:
            self._visit_assignment(tup, tup.elts, tup.ctx)
        elif tup.ctx == ast.Load:
            self._visit_starunpack(tup, tup.elts, ops.BUILD_TUPLE, ops.BUILD_TUPLE, ops.BUILD_TUPLE_UNPACK)
        else:
            self.visit_sequence(tup.elts)

    def visit_List(self, l):
        self.update_position(l.lineno)
        if l.ctx == ast.Store:
            self._visit_assignment(l, l.elts, l.ctx)
        elif l.ctx == ast.Load:
            self._visit_starunpack(l, l.elts, ops.BUILD_LIST, ops.BUILD_TUPLE, ops.BUILD_LIST_UNPACK)
        else:
            self.visit_sequence(l.elts)

    def visit_Dict(self, d):
        self.update_position(d.lineno)
        containers = 0
        elements = 0
        is_unpacking = False
        if d.values:
            for i in range(len(d.values)):
                key = d.keys[i]
                is_unpacking = key is None
                if elements == 0xFFFF or (elements and is_unpacking):
                    self.emit_op_arg(ops.BUILD_MAP, elements)
                    containers += 1
                    elements = 0
                if is_unpacking:
                    d.values[i].walkabout(self)
                    containers += 1
                else:
                    key.walkabout(self)
                    d.values[i].walkabout(self)
                    elements += 1
        if elements or containers == 0:
            self.emit_op_arg(ops.BUILD_MAP, elements)
            containers += 1
        # If there is more than one dict, they need to be merged into
        # a new dict. If there is one dict and it's an unpacking, then
        #it needs to be copied into a new dict.
        while containers > 1 or is_unpacking:
            oparg = min(containers, 255)
            self.emit_op_arg(ops.BUILD_MAP_UNPACK, oparg)
            containers -= (oparg - 1)
            is_unpacking = False

    def visit_Set(self, s):
        self._visit_starunpack(s, s.elts, ops.BUILD_SET, ops.BUILD_SET, ops.BUILD_SET_UNPACK)

    def visit_Name(self, name):
        self.update_position(name.lineno)
        self.name_op(name.id, name.ctx)

    def visit_NameConstant(self, node):
        self.update_position(node.lineno)
        self.load_const(node.single)

    def visit_keyword(self, keyword):
        if keyword.arg is not None:
            self.load_const(self.space.wrap(keyword.arg.decode('utf-8')))
        keyword.value.walkabout(self)

    def _make_call(self, n, # args already pushed
                   args, keywords):
        call_type = 0
        # the number of tuples and dictionaries on the stack
        nsubargs = 0
        nsubkwargs = 0
        nkw = 0
        nseen = 0 # the number of positional arguments on the stack
        if args is not None:
            for elt in args:
                if isinstance(elt, ast.Starred):
                    # A star-arg. If we've seen positional arguments,
                    # pack the positional arguments into a tuple.
                    if nseen:
                        self.emit_op_arg(ops.BUILD_TUPLE, nseen)
                        nseen = 0
                        nsubargs += 1
                    elt.value.walkabout(self)
                    nsubargs += 1
                elif nsubargs:
                    # We've seen star-args already, so we
                    # count towards items-to-pack-into-tuple.
                    elt.walkabout(self)
                    nseen += 1
                else:
                    # Positional arguments before star-arguments
                    # are left on the stack.
                    elt.walkabout(self)
                    n += 1
            if nseen:
                # Pack up any trailing positional arguments.
                self.emit_op_arg(ops.BUILD_TUPLE, nseen)
                nsubargs += 1
            if nsubargs:
                call_type |= 1
                if nsubargs > 1:
                    # If we ended up with more than one stararg, we need
                    # to concatenate them into a single sequence.
                    self.emit_op_arg(ops.BUILD_LIST_UNPACK, nsubargs)

        # Repeat procedure for keyword args
        nseen = 0 # the number of keyword arguments on the stack following
        if keywords is not None:
            for kw in keywords:
                if kw.arg is None:
                    # A keyword argument unpacking.
                    if nseen:
                        self.emit_op_arg(ops.BUILD_MAP, nseen)
                        nseen = 0
                        nsubkwargs += 1
                    kw.value.walkabout(self)
                    nsubkwargs += 1
                elif nsubkwargs:
                    # A keyword argument and we already have a dict.
                    self.load_const(self.space.wrap(kw.arg.decode('utf-8')))
                    kw.value.walkabout(self)
                    nseen += 1
                else:
                    # keyword argument
                    kw.walkabout(self)
                    nkw += 1
            if nseen:
                # Pack up any trailing keyword arguments.
                self.emit_op_arg(ops.BUILD_MAP,nseen)
                nsubkwargs += 1
            if nsubkwargs:
                call_type |= 2
                if nsubkwargs > 1:
                    # Pack it all up
                    function_pos = n + (call_type & 1) + nkw + 1
                    self.emit_op_arg(ops.BUILD_MAP_UNPACK_WITH_CALL, (nsubkwargs | (function_pos << 8)))

        assert n < 1<<8
        assert nkw < 1<<24
        n |= nkw << 8;

        op = 0
        if call_type == 0:
            op = ops.CALL_FUNCTION
        elif call_type == 1:
            op = ops.CALL_FUNCTION_VAR
        elif call_type == 2:
            op = ops.CALL_FUNCTION_KW
        elif call_type == 3:
            op = ops.CALL_FUNCTION_VAR_KW
        self.emit_op_arg(op, n)

    def visit_Call(self, call):
        self.update_position(call.lineno)
        if self._optimize_method_call(call):
            return
        call.func.walkabout(self)
        self._make_call(0, call.args, call.keywords)

    def _call_has_no_star_args(self, call):
        if call.args is not None:
            for elt in call.args:
                if isinstance(elt, ast.Starred):
                    return False
        if call.keywords is not None:
            for kw in call.keywords:
                if kw.arg is None:
                    return False
        return True

    def _call_has_simple_args(self, call):
        return self._call_has_no_star_args(call) and not call.keywords

    def _optimize_method_call(self, call):
        if not self._call_has_no_star_args(call) or \
           not isinstance(call.func, ast.Attribute):
            return False
        attr_lookup = call.func
        assert isinstance(attr_lookup, ast.Attribute)
        attr_lookup.value.walkabout(self)
        self.emit_op_name(ops.LOOKUP_METHOD, self.names, attr_lookup.attr)
        self.visit_sequence(call.args)
        arg_count = len(call.args) if call.args is not None else 0
        self.visit_sequence(call.keywords)
        kwarg_count = len(call.keywords) if call.keywords is not None else 0
        self.emit_op_arg(ops.CALL_METHOD, (kwarg_count << 8) | arg_count)
        return True

    def visit_ListComp(self, lc):
        self._compile_comprehension(lc, "<listcomp>",
                                    ComprehensionCodeGenerator)

    def _comp_generator(self, node, generators, gen_index):
        start = self.new_block()
        if_cleanup = self.new_block()
        anchor = self.new_block()
        gen = generators[gen_index]
        assert isinstance(gen, ast.comprehension)
        if gen_index == 0:
            self.argcount = 1
            self.emit_op_arg(ops.LOAD_FAST, 0)
        else:
            gen.iter.walkabout(self)
            self.emit_op(ops.GET_ITER)
        self.use_next_block(start)
        self.emit_jump(ops.FOR_ITER, anchor)
        self.use_next_block()
        gen.target.walkabout(self)
        if gen.ifs:
            for if_ in gen.ifs:
                if_.accept_jump_if(self, False, if_cleanup)
                self.use_next_block()
        gen_index += 1
        if gen_index < len(generators):
            self._comp_generator(node, generators, gen_index)
        else:
            node.accept_comp_iteration(self, gen_index)
        self.use_next_block(if_cleanup)
        self.emit_jump(ops.JUMP_ABSOLUTE, start, True)
        self.use_next_block(anchor)

    def _compile_comprehension(self, node, name, sub_scope):
        code, qualname = self.sub_scope(sub_scope, name, node, node.lineno)
        self.update_position(node.lineno)
        self._make_function(code, qualname=qualname)
        first_comp = node.get_generators()[0]
        assert isinstance(first_comp, ast.comprehension)
        first_comp.iter.walkabout(self)
        self.emit_op(ops.GET_ITER)
        self.emit_op_arg(ops.CALL_FUNCTION, 1)

    def visit_GeneratorExp(self, genexp):
        self._compile_comprehension(genexp, "<genexpr>", GenExpCodeGenerator)

    def visit_SetComp(self, setcomp):
        self._compile_comprehension(setcomp, "<setcomp>",
                                    ComprehensionCodeGenerator)

    def visit_DictComp(self, dictcomp):
        self._compile_comprehension(dictcomp, "<dictcomp>",
                                    ComprehensionCodeGenerator)

    def visit_Attribute(self, attr):
        self.update_position(attr.lineno)
        names = self.names
        ctx = attr.ctx
        if ctx != ast.AugStore:
            attr.value.walkabout(self)
        if ctx == ast.AugLoad:
            self.emit_op(ops.DUP_TOP)
            self.emit_op_name(ops.LOAD_ATTR, names, attr.attr)
        elif ctx == ast.Load:
            self.emit_op_name(ops.LOAD_ATTR, names, attr.attr)
        elif ctx == ast.AugStore:
            self.emit_op(ops.ROT_TWO)
            self.emit_op_name(ops.STORE_ATTR, names, attr.attr)
        elif ctx == ast.Store:
            self.emit_op_name(ops.STORE_ATTR, names, attr.attr)
        elif ctx == ast.Del:
            self.emit_op_name(ops.DELETE_ATTR, names, attr.attr)
        else:
            raise AssertionError("unknown context")

    def _complex_slice(self, slc, ctx):
        if slc.lower:
            slc.lower.walkabout(self)
        else:
            self.load_const(self.space.w_None)
        if slc.upper:
            slc.upper.walkabout(self)
        else:
            self.load_const(self.space.w_None)
        arg = 2
        if slc.step:
            slc.step.walkabout(self)
            arg += 1
        self.emit_op_arg(ops.BUILD_SLICE, arg)

    def _nested_slice(self, slc, ctx):
        if isinstance(slc, ast.Slice):
            self._complex_slice(slc, ctx)
        elif isinstance(slc, ast.Index):
            slc.value.walkabout(self)
        else:
            raise AssertionError("unknown nested slice type")

    def _compile_slice(self, slc, ctx):
        if isinstance(slc, ast.Index):
            if ctx != ast.AugStore:
                slc.value.walkabout(self)
        elif isinstance(slc, ast.Slice):
            if ctx != ast.AugStore:
                self._complex_slice(slc, ctx)
        elif isinstance(slc, ast.ExtSlice):
            if ctx != ast.AugStore:
                for dim in slc.dims:
                    self._nested_slice(dim, ctx)
                self.emit_op_arg(ops.BUILD_TUPLE, len(slc.dims))
        else:
            raise AssertionError("unknown slice type")
        if ctx == ast.AugLoad:
            self.emit_op(ops.DUP_TOP_TWO)
        elif ctx == ast.AugStore:
            self.emit_op(ops.ROT_THREE)
        self.emit_op(subscr_operations(ctx))

    def visit_Subscript(self, sub):
        self.update_position(sub.lineno)
        if sub.ctx != ast.AugStore:
            sub.value.walkabout(self)
        self._compile_slice(sub.slice, sub.ctx)

    def visit_JoinedStr(self, joinedstr):
        self.update_position(joinedstr.lineno)
        for node in joinedstr.values:
            node.walkabout(self)
        self.emit_op_arg(ops.BUILD_STRING, len(joinedstr.values))

    def visit_FormattedValue(self, fmt):
        fmt.value.walkabout(self)
        arg = 0
        if fmt.conversion == ord('s'): arg = consts.FVC_STR
        if fmt.conversion == ord('r'): arg = consts.FVC_REPR
        if fmt.conversion == ord('a'): arg = consts.FVC_ASCII
        self.emit_op_arg(ops.FORMAT_VALUE, arg)


class TopLevelCodeGenerator(PythonCodeGenerator):

    def __init__(self, space, tree, symbols, compile_info):
        PythonCodeGenerator.__init__(self, space, "<module>", tree, -1,
                                     symbols, compile_info, qualname=None)

    def _compile(self, tree):
        tree.walkabout(self)

    def _get_code_flags(self):
        flags = 0
        if not self.cell_vars and not self.free_vars:
            flags |= consts.CO_NOFREE
        if self.scope.doc_removable:
            flags |= consts.CO_KILL_DOCSTRING
        return flags


class AbstractFunctionCodeGenerator(PythonCodeGenerator):

    def _get_code_flags(self):
        scope = self.scope
        assert isinstance(scope, symtable.FunctionScope)
        flags = consts.CO_NEWLOCALS
        if scope.optimized:
            flags |= consts.CO_OPTIMIZED
        if scope.nested:
            flags |= consts.CO_NESTED
        if scope.is_generator:
            flags |= consts.CO_GENERATOR
        if scope.has_yield_inside_try:
            flags |= consts.CO_YIELD_INSIDE_TRY
        if scope.has_variable_arg:
            flags |= consts.CO_VARARGS
        if scope.has_keywords_arg:
            flags |= consts.CO_VARKEYWORDS
        if scope.doc_removable:
            flags |= consts.CO_KILL_DOCSTRING
        if not self.cell_vars and not self.free_vars:
            flags |= consts.CO_NOFREE
        return PythonCodeGenerator._get_code_flags(self) | flags


class FunctionCodeGenerator(AbstractFunctionCodeGenerator):

    def _compile(self, func):
        assert isinstance(func, ast.FunctionDef)
        has_docstring = self.ensure_docstring_constant(func.body)
        start = 1 if has_docstring else 0
        args = func.args
        assert isinstance(args, ast.arguments)
        if args.args:
            self.argcount = len(args.args)
        if args.kwonlyargs:
            self.kwonlyargcount = len(args.kwonlyargs)
        if func.body:
            for i in range(start, len(func.body)):
                func.body[i].walkabout(self)

class AsyncFunctionCodeGenerator(AbstractFunctionCodeGenerator):

    def _compile(self, func):
        assert isinstance(func, ast.AsyncFunctionDef)
        has_docstring = self.ensure_docstring_constant(func.body)
        start = 1 if has_docstring else 0
        args = func.args
        assert isinstance(args, ast.arguments)
        if args.args:
            self.argcount = len(args.args)
        if args.kwonlyargs:
            self.kwonlyargcount = len(args.kwonlyargs)
        if func.body:
            for i in range(start, len(func.body)):
                func.body[i].walkabout(self)

    def _get_code_flags(self):
        flags = AbstractFunctionCodeGenerator._get_code_flags(self)
        return flags | consts.CO_COROUTINE

class LambdaCodeGenerator(AbstractFunctionCodeGenerator):

    def _compile(self, lam):
        assert isinstance(lam, ast.Lambda)
        args = lam.args
        assert isinstance(args, ast.arguments)
        if args.args:
            self.argcount = len(args.args)
        if args.kwonlyargs:
            self.kwonlyargcount = len(args.kwonlyargs)
        # Prevent a string from being the first constant and thus a docstring.
        self.add_const(self.space.w_None)
        lam.body.walkabout(self)
        self.emit_op(ops.RETURN_VALUE)


class ComprehensionCodeGenerator(AbstractFunctionCodeGenerator):

    def _compile(self, node):
        assert isinstance(node, ast.expr)
        self.update_position(node.lineno)
        node.build_container(self)
        self._comp_generator(node, node.get_generators(), 0)
        self._end_comp()

    def _end_comp(self):
        self.emit_op(ops.RETURN_VALUE)


class GenExpCodeGenerator(ComprehensionCodeGenerator):

    def _end_comp(self):
        pass

    def _get_code_flags(self):
        flags = ComprehensionCodeGenerator._get_code_flags(self)
        return flags | consts.CO_GENERATOR


class ClassCodeGenerator(PythonCodeGenerator):

    def _compile(self, cls):
        assert isinstance(cls, ast.ClassDef)
        self.ensure_docstring_constant(cls.body)
        self.lineno = self.first_lineno
        self.argcount = 1
        # load (global) __name__ ...
        self.name_op("__name__", ast.Load)
        # ... and store it as __module__
        self.name_op("__module__", ast.Store)
        # store the qualname
        w_qualname = self.space.wrap(self.qualname.decode("utf-8"))
        self.load_const(w_qualname)
        self.name_op("__qualname__", ast.Store)
        # compile the body proper
        self._handle_body(cls.body)
        # return the (empty) __class__ cell
        scope = self.scope.lookup("__class__")
        if scope == symtable.SCOPE_CELL_CLASS:
            # Return the cell where to store __class__
            self.emit_op_arg(ops.LOAD_CLOSURE, self.cell_vars["__class__"])
        else:
            # This happens when nobody references the cell
            self.load_const(self.space.w_None)
        self.emit_op(ops.RETURN_VALUE)

    def _get_code_flags(self):
        flags = 0
        if self.scope.doc_removable:
            flags |= consts.CO_KILL_DOCSTRING
        return PythonCodeGenerator._get_code_flags(self) | flags
