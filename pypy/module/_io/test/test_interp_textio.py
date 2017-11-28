import pytest
try:
    from hypothesis import given, strategies as st, assume
except ImportError:
    pytest.skip("hypothesis required")
from pypy.module._io.interp_bytesio import W_BytesIO
from pypy.module._io.interp_textio import W_TextIOWrapper, DecodeBuffer

LINESEP = ['', '\r', '\n', '\r\n']

@st.composite
def text_with_newlines(draw):
    sep = draw(st.sampled_from(LINESEP))
    lines = draw(st.lists(st.text(max_size=10), max_size=10))
    return sep.join(lines)

@given(txt=text_with_newlines(),
       mode=st.sampled_from(['\r', '\n', '\r\n', '']),
       limit=st.integers(min_value=-1))
def test_readline(space, txt, mode, limit):
    assume(limit != 0)
    w_stream = W_BytesIO(space)
    w_stream.descr_init(space, space.newbytes(txt.encode('utf-8')))
    w_textio = W_TextIOWrapper(space)
    w_textio.descr_init(
        space, w_stream, encoding='utf-8',
        w_newline=space.newtext(mode))
    lines = []
    while True:
        w_line = w_textio.readline_w(space, space.newint(limit))
        line = space.utf8_w(w_line).decode('utf-8')
        if limit > 0:
            assert len(line) <= limit
        if line:
            lines.append(line)
        else:
            break
    assert u''.join(lines) == txt

@given(st.text())
def test_read_buffer(text):
    buf = DecodeBuffer(text.encode('utf-8'))
    assert buf.get_chars(-1) == text.encode('utf-8')
    assert buf.exhausted()

@given(st.text(), st.lists(st.integers(min_value=0)))
def test_readn_buffer(text, sizes):
    buf = DecodeBuffer(text.encode('utf-8'))
    strings = []
    for n in sizes:
        s = buf.get_chars(n)
        if not buf.exhausted():
            assert len(s.decode('utf-8')) == n
        else:
            assert len(s.decode('utf-8')) <= n
        strings.append(s)
    assert ''.join(strings) == text[:sum(sizes)].encode('utf-8')

@given(st.text())
def test_next_char(text):
    buf = DecodeBuffer(text.encode('utf-8'))
    for i in range(len(text)):
        ch = buf.next_char()
        assert ch == text[i].encode('utf-8')[0]
    assert buf.exhausted()
