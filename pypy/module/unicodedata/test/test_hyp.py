import pytest
try:
    from hypothesis import given, strategies as st, example, settings
except ImportError:
    pytest.skip("hypothesis required")

from pypy.module.unicodedata.interp_ucd import ucd

def make_normalization(space, NF_code):
    def normalize(s):
        w_s = space.newunicode(s)
        w_res = ucd.normalize(space, NF_code, w_s)
        return space.unwrap(w_res)
    return normalize

all_forms = ['NFC', 'NFD', 'NFKC', 'NFKD']

# For every (n1, n2, n3) triple, applying n1 then n2 must be the same
# as applying n3.
# Reference: http://unicode.org/reports/tr15/#Design_Goals
compositions = [
    ('NFC', 'NFC', 'NFC'),
    ('NFC', 'NFD', 'NFD'),
    ('NFC', 'NFKC', 'NFKC'),
    ('NFC', 'NFKD', 'NFKD'),
    ('NFD', 'NFC', 'NFC'),
    ('NFD', 'NFD', 'NFD'),
    ('NFD', 'NFKC', 'NFKC'),
    ('NFD', 'NFKD', 'NFKD'),
    ('NFKC', 'NFC', 'NFKC'),
    ('NFKC', 'NFD', 'NFKD'),
    ('NFKC', 'NFKC', 'NFKC'),
    ('NFKC', 'NFKD', 'NFKD'),
    ('NFKD', 'NFC', 'NFKC'),
    ('NFKD', 'NFD', 'NFKD'),
    ('NFKD', 'NFKC', 'NFKC'),
    ('NFKD', 'NFKD', 'NFKD'),
]


@pytest.mark.parametrize('NF1, NF2, NF3', compositions)
@example(s=u'---\uafb8\u11a7---')  # issue 2289
@settings(max_examples=1000)
@given(s=st.text())
def test_composition(s, space, NF1, NF2, NF3):
    norm1, norm2, norm3 = [make_normalization(space, form) for form in [NF1, NF2, NF3]]
    assert norm2(norm1(s)) == norm3(s)
