

class AppTest_Descroperation:

    def test_getslice(self):
        class Sq(object):
            def __getslice__(self, start, stop):
                return (start, stop)

            def __getitem__(self, key):
                return "booh"

        sq = Sq()

        assert sq[1:3] == (1,3)
