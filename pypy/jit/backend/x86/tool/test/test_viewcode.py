from cStringIO import StringIO
from pypy.jit.backend.x86.tool.viewcode import format_code_dump_with_labels

def test_format_code_dump_with_labels():
    lines = StringIO("""
aa00 <.data>:
aa00: one
aa01: two
aa03: three
aa04: for
aa05: five
aa06: six
aa0c: seven
aa12: eight
""".strip()).readlines()
    #
    labels = [(0x00, 'AAA'), (0x03, 'BBB'), (0x0c, 'CCC')]
    lines = format_code_dump_with_labels(0xAA00, lines, labels)
    out = ''.join(lines)
    assert out == """
aa00 <.data>:

AAA
aa00: one
aa01: two

BBB
aa03: three
aa04: for
aa05: five
aa06: six

CCC
aa0c: seven
aa12: eight
""".strip()


def test_format_code_dump_with_labels_no_labels():
    input = """
aa00 <.data>:
aa00: one
aa01: two
aa03: three
aa04: for
aa05: five
aa06: six
aa0c: seven
aa12: eight
""".strip()
    lines = StringIO(input).readlines()
    #
    lines = format_code_dump_with_labels(0xAA00, lines, labels=None)
    out = ''.join(lines)
    assert out.strip() == input
