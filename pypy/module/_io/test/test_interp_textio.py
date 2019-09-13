import pytest
try:
    from hypothesis import given, strategies as st, settings, example
except ImportError:
    pytest.skip("hypothesis required")
import os
from pypy.module._io.interp_bytesio import W_BytesIO
from pypy.module._io.interp_textio import W_TextIOWrapper, DecodeBuffer

# workaround suggestion for slowness by David McIver:
# force hypothesis to initialize some lazy stuff
# (which takes a lot of time, which trips the timer otherwise)
st.text().example()

def translate_newlines(text):
    text = text.replace(u'\r\n', u'\n')
    text = text.replace(u'\r', u'\n')
    return text.replace(u'\n', os.linesep)

@st.composite
def st_readline(draw, st_nlines=st.integers(min_value=0, max_value=10)):
    n_lines = draw(st_nlines)
    fragments = []
    limits = []
    for _ in range(n_lines):
        line = draw(st.text(st.characters(blacklist_characters=u'\r\n')))
        fragments.append(line)
        ending = draw(st.sampled_from([u'\n', u'\r', u'\r\n']))
        fragments.append(ending)
        limit = draw(st.integers(min_value=0, max_value=len(line) + 5))
        limits.append(limit)
        limits.append(-1)
    return (u''.join(fragments), limits)

@given(data=st_readline(),
       mode=st.sampled_from(['\r', '\n', '\r\n', '']))
@settings(deadline=None, database=None)
@example(data=(u'\n\r\n', [0, -1, 2, -1, 0, -1]), mode='\r')
def test_readline(space, data, mode):
    txt, limits = data
    w_stream = W_BytesIO(space)
    w_stream.descr_init(space, space.newbytes(txt.encode('utf-8')))
    w_textio = W_TextIOWrapper(space)
    w_textio.descr_init(
        space, w_stream,
        encoding='utf-8', w_errors=space.newtext('surrogatepass'),
        w_newline=space.newtext(mode))
    lines = []
    for limit in limits:
        w_line = w_textio.readline_w(space, space.newint(limit))
        line = space.utf8_w(w_line).decode('utf-8')
        if limit >= 0:
            assert len(line) <= limit
        if line:
            lines.append(line)
        elif limit:
            break
    assert txt.startswith(u''.join(lines))

@given(st.text())
def test_read_buffer(text):
    buf = DecodeBuffer(text.encode('utf8'), len(text))
    chars, size = buf.get_chars(-1)
    assert chars.decode('utf8') == text
    assert len(text) == size
    assert buf.exhausted()

@given(st.text(), st.lists(st.integers(min_value=0)))
@example(u'\x80', [1])
def test_readn_buffer(text, sizes):
    buf = DecodeBuffer(text.encode('utf8'), len(text))
    strings = []
    for n in sizes:
        chars, size = buf.get_chars(n)
        s = chars.decode('utf8')
        assert size == len(s)
        if not buf.exhausted():
            assert len(s) == n
        else:
            assert len(s) <= n
        strings.append(s)
    assert ''.join(strings) == text[:sum(sizes)]

@given(st.text())
def test_next_char(text):
    buf = DecodeBuffer(text.encode('utf8'), len(text))
    for i in range(len(text)):
        ch = buf.next_char()
        assert ch == text[i].encode('utf-8')
    assert buf.exhausted()
