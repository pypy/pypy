import types

from rpython.flowspace import flowcontext, operation
from rpython.flowspace.bytecode import lnotab_linetable
from rpython.tool.error import offset2lineno


def test_linetable():
    source = ('def f(x):\n    y = x\n    if x:\n%s        return 1\n'
              '%s    return y\n')
    namespace = {}
    exec(compile(source % ('\n' * 300, '\n' * 1000), '<test>', 'exec'),
         namespace)
    codes = [namespace['f'].__code__]
    for module in [flowcontext, operation]:
        for obj in vars(module).values():
            for func in vars(obj).values() if isinstance(obj, type) else [obj]:
                code = getattr(func, '__code__', None)
                if isinstance(code, types.CodeType):
                    codes.append(code)
    assert len(codes) > 50
    for code in codes:
        table = lnotab_linetable(code.co_firstlineno, code.co_lnotab)
        for offset in range(len(code.co_code)):
            assert (table.offset2lineno(offset) ==
                    offset2lineno(code, offset))
