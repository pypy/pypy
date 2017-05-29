import pytest
from hypothesis import strategies as st
from hypothesis import given, settings, example

from unicodedata import normalize

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

@pytest.mark.parametrize('norm1, norm2, norm3', compositions)
@settings(max_examples=1000)
@example(s=u'---\uafb8\u11a7---')  # issue 2289
@given(s=st.text())
def test_composition(s, norm1, norm2, norm3):
    assert normalize(norm2, normalize(norm1, s)) == normalize(norm3, s)
