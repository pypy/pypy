from pypy.translator.squeak.message import Message

class TestMessage:

    def test_symbol(self):
        assert Message("bla_bla").symbol(0) == "blaBla"
        assert Message("bla").symbol(1) == "bla:"
        assert Message("bla_bla_bla").symbol(3) == "blaBlaBla:with:with:"
        assert Message("+").symbol(1) == "+"

    def test_signature(self):
        assert Message("bla").signature([]) == "bla"
        assert Message("bla").signature(["v"]) == "bla: v"
        assert Message("bla").signature(["v0", "v1"]) == "bla: v0 with: v1"
        assert Message("+").signature(["v"]) == "+ v"

