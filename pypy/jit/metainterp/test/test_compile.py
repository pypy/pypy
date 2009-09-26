from pypy.jit.metainterp.history import LoopToken, ConstInt
from pypy.jit.metainterp.specnode import NotSpecNode, ConstantSpecNode
from pypy.jit.metainterp.compile import insert_loop_token


def test_insert_loop_token():
    lst = []
    #
    tok1 = LoopToken()
    tok1.specnodes = [NotSpecNode()]
    insert_loop_token(lst, tok1)
    assert lst == [tok1]
    #
    tok2 = LoopToken()
    tok2.specnodes = [ConstantSpecNode(ConstInt(8))]
    insert_loop_token(lst, tok2)
    assert lst == [tok2, tok1]
    #
    tok3 = LoopToken()
    tok3.specnodes = [ConstantSpecNode(ConstInt(-13))]
    insert_loop_token(lst, tok3)
    assert lst == [tok2, tok3, tok1]
