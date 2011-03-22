from pypy.interpreter.astcompiler import ast
from pypy.tool import stdlib___future__ as future

def get_futures(future_flags, tree):
    flags = 0
    pos = (-1, 0)

    if isinstance(tree, ast.Module):
        stmts = tree.body
    elif isinstance(tree, ast.Interactive):
        stmts = tree.body
    else:
        return flags, pos

    if stmts is None:
        return flags, pos

    found_docstring = False

    for elem in stmts:
        if isinstance(elem, ast.ImportFrom):
            if elem.module != '__future__':
                break
            for alias in elem.names:
                if not isinstance(alias, ast.alias):
                    continue
                name = alias.name
                try:
                    flags |= future_flags.compiler_features[name]
                except KeyError:
                    pass
                pos = elem.lineno, elem.col_offset
        elif isinstance(elem, ast.Expr):
            if found_docstring:
                break
            if isinstance(elem.value, ast.Str):
                found_docstring = True
    return flags, pos

class FutureFlags(object):

    def __init__(self, version):
        compiler_flags = 0
        self.compiler_features = {}
        self.mandatory_flags = 0
        for fname in future.all_feature_names:
            feature = getattr(future, fname)
            if version >= feature.getOptionalRelease():
                flag = feature.compiler_flag
                compiler_flags |= flag
                self.compiler_features[fname] = flag
            if version >= feature.getMandatoryRelease():
                self.mandatory_flags |= feature.compiler_flag
        self.allowed_flags = compiler_flags

    def get_flag_names(self, space, flags):
        flag_names = []
        for name, value in self.compiler_features.items():
            if flags & value:
                flag_names.append(name)
        return flag_names

futureFlags_2_4 = FutureFlags((2, 4, 4, 'final', 0))
futureFlags_2_5 = FutureFlags((2, 5, 0, 'final', 0))
futureFlags_2_7 = FutureFlags((2, 7, 0, 'final', 0))
