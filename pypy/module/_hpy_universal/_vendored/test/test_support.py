from . import support

def test_expand_template():
    expanded = support.expand_template("""
        @EXPORT test_f HPy_METH_NOARGS
        @EXPORT test_g METH_O
        @EXPORT test_h METH_VARARGS | METH_KEYWORDS
        some more C stuff
        @INIT
    """, name='mytest')
    method_table = [
        '{"test_f", test_f, HPy_METH_NOARGS, NULL},',
        '{"test_g", (HPyMeth)test_g, METH_O, NULL},',
        '{"test_h", (HPyMeth)test_h, METH_VARARGS | METH_KEYWORDS, NULL},'
        ]
    methods = '\n    '.join(method_table)
    init_code = support.INIT_TEMPLATE % {'methods': methods, 'name': 'mytest'}
    assert expanded.rstrip() == f"""#include <hpy.h>

        some more C stuff
{init_code}
""".rstrip()
