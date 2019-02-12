import pytest
try:
    from hypothesis import given, strategies as st, settings
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
        line = space.unicode_w(w_line)
        if limit >= 0:
            assert len(line) <= limit
        if line:
            lines.append(line)
        elif limit:
            break
    assert txt.startswith(u''.join(lines))

@given(st.text())
def test_read_buffer(text):
    buf = DecodeBuffer(text)
    assert buf.get_chars(-1) == text
    assert buf.exhausted()

@given(st.text(), st.lists(st.integers(min_value=0)))
def test_readn_buffer(text, sizes):
    buf = DecodeBuffer(text)
    strings = []
    for n in sizes:
        s = buf.get_chars(n)
        if not buf.exhausted():
            assert len(s) == n
        else:
            assert len(s) <= n
        strings.append(s)
    assert ''.join(strings) == text[:sum(sizes)]

@given(st.text())
def test_next_char(text):
    buf = DecodeBuffer(text)
    chars = []
    try:
        while True:
            chars.append(buf.next_char())
    except StopIteration:
        pass
    assert buf.exhausted()
    assert u''.join(chars) == text
