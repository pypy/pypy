import dis
import io

def compare_lines(t1, t2):
    for l1, l2 in zip(t1.split('\n'), t2.split('\n')):
        if 'LOAD_CONST' in l1:
            # some small variation is OK
            assert 'LOAD_CONST' in l2
        else:
            assert l1.strip() == l2.strip()

def test_asyncFor():
    co = compile('''
async def f():
    class Iterable:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration


    async for i in Iterable():
        pass
    else:
        print('ok')
    ''', '<str>', 'exec')
    # Python 3.6 does not resursively call dis._disassemble, but we want
    # the dis of the "async for", which we can only access inside a "async def"
    result = io.StringIO()
    dis.dis(co.co_consts[0].co_code, file=result)
    cpython37 = """ 0 LOAD_BUILD_CLASS
          2 LOAD_CONST               1 (1)
          4 LOAD_CONST               2 (2)
          6 MAKE_FUNCTION            0
          8 LOAD_CONST               2 (2)
         10 CALL_FUNCTION            2
         12 STORE_FAST               0 (0)
         14 SETUP_LOOP              52 (to 68)
         16 LOAD_FAST                0 (0)
         18 CALL_FUNCTION            0
         20 GET_AITER
    >>   22 SETUP_EXCEPT            12 (to 36)
         24 GET_ANEXT
         26 LOAD_CONST               0 (0)
         28 YIELD_FROM
         30 STORE_FAST               1 (1)
         32 POP_BLOCK
         34 JUMP_ABSOLUTE           22
    >>   36 DUP_TOP
         38 LOAD_GLOBAL              0 (0)
         40 COMPARE_OP              10 (exception match)
         42 POP_JUMP_IF_TRUE        48
         44 END_FINALLY
         46 JUMP_ABSOLUTE           22
    >>   48 POP_TOP
         50 POP_TOP
         52 POP_TOP
         54 POP_EXCEPT
         56 POP_TOP
         58 POP_BLOCK
         60 LOAD_GLOBAL              1 (1)
         62 LOAD_CONST               3 (3)
         64 CALL_FUNCTION            1
         66 POP_TOP
    >>   68 LOAD_CONST               0 (0)
         70 RETURN_VALUE
"""

    compare_lines(cpython37, result.getvalue()) 
