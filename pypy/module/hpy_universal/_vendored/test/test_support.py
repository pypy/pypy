from . import support


def test_expand_template():
    expanded = support.expand_template("""
        @EXPORT test_f METH_O
        some more C stuff
        @INIT
    """, name='mytest')
    methods = '{"test_f", test_f, METH_O, NULL},'
    init_code = support.INIT_TEMPLATE % {'methods': methods, 'name': 'mytest'}
    assert expanded.rstrip() == f"""#include <hpy.h>

        some more C stuff
{init_code}
""".rstrip()
