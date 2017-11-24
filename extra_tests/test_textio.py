from hypothesis import given, strategies as st

from io import BytesIO, TextIOWrapper

LINESEP = ['', '\r', '\n', '\r\n']

@st.composite
def text_with_newlines(draw):
    sep = draw(st.sampled_from(LINESEP))
    lines = draw(st.lists(st.text(max_size=10), max_size=10))
    return sep.join(lines)

@given(txt=text_with_newlines(),
       mode=st.sampled_from(['\r', '\n', '\r\n', '']),
       limit=st.integers(min_value=-1))
def test_readline(txt, mode, limit):
    textio = TextIOWrapper(BytesIO(txt.encode('utf-8')), newline=mode)
    lines = []
    while True:
        line = textio.readline(limit)
        if limit > 0:
            assert len(line) < limit
        if line:
            lines.append(line)
        else:
            break
    assert u''.join(lines) == txt
