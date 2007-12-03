N = (2 ** 19 - 1)

u1 = (u"not the xyz" * N)
def test_find_worstcase():
    u1.find(u"not there")

def test_count_worstcase():
    u1.count(u"not there")

u2 = (u"aaa" * 1000)
def test_find_pattern16():
    i = 1
    while i < N:
        i += 1
        u2.find(u"bbbbbbbbbbbbbbbb")

def test_find_pattern8():
    i = 1
    while i < N:
        i += 1
        u2.find(u"bbbbbbbb")

def test_find_pattern4():
    i = 1
    while i < N:
        i += 1
        u2.find(u"bbbb")

def test_find_pattern2():
    i = 1
    while i < N:
        i += 1
        u2.find(u"bb")


def test_find_pattern1():
    i = 1
    while i < N:
        i += 1
        u2.find(u"b")
