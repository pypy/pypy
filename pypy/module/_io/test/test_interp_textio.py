from hypothesis import given, strategies as st, assume
from pypy.module._io.interp_bytesio import W_BytesIO
from pypy.module._io.interp_textio import W_TextIOWrapper

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
        line = space.unicode_w(w_textio.readline_w(space, space.newint(limit)))
        if limit > 0:
            assert len(line) <= limit
        if line:
            lines.append(line)
        else:
            break
    assert u''.join(lines) == txt
