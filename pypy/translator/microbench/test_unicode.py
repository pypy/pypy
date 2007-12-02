N = (2 ** 19 - 1)

u1 = (u"not the xyz" * N)
def test_find_worstcase():
    u1.find(u"not there")
