from pypy.interpreter.astcompiler import ast
class TestAstToObject:
    def test_types(self, space):
        assert space.issubtype_w(
                ast.get(space).w_Module, ast.get(space).w_mod)
                                  
    def test_num(self, space):
        value = space.wrap(42)
        node = ast.Num(value, lineno=1, col_offset=1)
        w_node = node.to_object(space)
        assert space.getattr(w_node, space.wrap("n")) is value

    def test_expr(self, space):
        value = space.wrap(42)
        node = ast.Num(value, lineno=1, col_offset=1)
        expr = ast.Expr(node, lineno=1, col_offset=1)
        w_node = expr.to_object(space)
        # node.value.n
        assert space.getattr(space.getattr(w_node, space.wrap("value")),
                             space.wrap("n")) is value

    def test_operation(self, space):
        val1 = ast.Num(space.wrap(1), lineno=1, col_offset=1)
        val2 = ast.Num(space.wrap(2), lineno=1, col_offset=1)
        node = ast.BinOp(left=val1, right=val2, op=ast.Add,
                         lineno=1, col_offset=1)
        w_node = node.to_object(space)
        w_op = space.getattr(w_node, space.wrap("op"))
        assert space.isinstance_w(w_op, ast.get(space).w_operator)

    def test_from_object(self, space):
        value = space.wrap(42)
        w_node = space.call_function(ast.get(space).w_Num)
        space.setattr(w_node, space.wrap('n'), value)
        space.setattr(w_node, space.wrap('lineno'), space.wrap(1))
        space.setattr(w_node, space.wrap('col_offset'), space.wrap(1))
        node = ast.Num.from_object(space, w_node)
        assert node.n is value

    def test_fields(self, space):
        w_fields = space.getattr(ast.get(space).w_FunctionDef,
                                 space.wrap("_fields"))
        assert space.eq_w(w_fields, space.wrap(
            ('name', 'args', 'body', 'decorator_list')))
        w_fields = space.getattr(ast.get(space).w_arguments,
                                 space.wrap("_fields"))
        assert space.eq_w(w_fields, space.wrap(
            ('args', 'vararg', 'kwarg', 'defaults')))
        
    def test_attributes(self, space):
        w_attrs = space.getattr(ast.get(space).w_FunctionDef,
                                space.wrap("_attributes"))
        assert space.eq_w(w_attrs, space.wrap(('lineno', 'col_offset')))
        
