
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.jvm.platform import Jvm

class TestJvmPlatform(JvmTest):
    def test_basic_interaction(self):
        def fn():
            rand = Jvm.Random()
            x = rand.nextInt()
            return x

        ret = self.interpret(fn, [])
        assert isinstance(ret, int)
