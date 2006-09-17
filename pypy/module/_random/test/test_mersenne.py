from pypy.module._random.rpy_random import Random

# the numbers were created by using CPython's _randommodule.c

def test_init_from_seed():
    rnd = Random(1000)
    assert rnd.state[:14] == [1000, 4252021385, 1724402292, 571538732,
            73690720, 4283493349, 2222270404, 2464917285, 427676011,
            1101193792, 2887716015, 3670250828, 1664757559, 1538426459]

def test_numbers():
    rnd = Random(1000)
    nums = [rnd.genrand32() for i in range(14)]
    assert nums == [2807145907, 882709079, 493951047, 2621574848, 4081433851,
            44058974, 2070996316, 1549632257, 3747249597, 3650674304,
            911961945, 58396205, 174846504, 1478498153]

