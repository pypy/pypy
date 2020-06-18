class AppTestFstring:
    def test_error_unknown_code(self):
        """
        def fn():
            f'{1000:j}'
        exc_info = raises(ValueError, fn)
        assert str(exc_info.value).startswith("Unknown format code")
        """

    def test_ast_lineno_and_col_offset(self):
        import ast
        m = ast.parse("\nf'a{x}bc{y}de'")
        x_ast = m.body[0].value.values[1].value
        y_ast = m.body[0].value.values[3].value
        assert x_ast.lineno == 2
        assert x_ast.col_offset == 4
        assert y_ast.lineno == 2
        assert y_ast.col_offset == 9

    def test_ast_mutiline_lineno_and_col_offset(self):
        import ast
        m = ast.parse("\n\nf'''{x}\nabc{y}\n{\nz}'''   \n\n\n")
        x_ast = m.body[0].value.values[0].value
        y_ast = m.body[0].value.values[2].value
        z_ast = m.body[0].value.values[4].value
        assert x_ast.lineno == 3
        assert x_ast.col_offset == 5
        assert y_ast.lineno == 4
        assert y_ast.col_offset == 5
        assert z_ast.lineno == 6
        assert z_ast.col_offset == 0
