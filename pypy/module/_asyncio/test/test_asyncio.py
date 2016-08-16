class AppTestAsyncIO(object):
    
    spaceconfig = dict(usemodules=["select","_socket","thread","signal",
                                   "struct","_multiprocessing","array",
                                   "_posixsubprocess","fcntl",
                                   "unicodedata"])
    
    def test_gil_issue(self):
        # the problem occured at await asyncio.open_connection
        # after calling run_until_complete
        """
        import encodings.idna
        import asyncio
        async def f():
            reader, writer = await asyncio.open_connection('example.com', 80)
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(f())
        print("done with async loop")
        """
    
    def test_asynchronous_context_managers(self):
        """
import encodings.idna
import asyncio

class Corotest(object):
    def __init__(self):
        self.res = "-"
    
    async def coro(self, name, lock):
        self.res += ' coro {}: waiting for lock -'.format(name)
        async with lock:
            self.res += ' coro {}: holding the lock -'.format(name)
            await asyncio.sleep(1)
            self.res += ' coro {}: releasing the lock -'.format(name)

cor = Corotest()
loop = asyncio.get_event_loop()
lock = asyncio.Lock()
coros = asyncio.gather(cor.coro(1, lock), cor.coro(2, lock))
try:
    loop.run_until_complete(coros)
finally:
    loop.close()

assert "coro 1: waiting for lock" in cor.res
assert "coro 1: holding the lock" in cor.res
assert "coro 1: releasing the lock" in cor.res
assert "coro 2: waiting for lock" in cor.res
assert "coro 2: holding the lock" in cor.res
assert "coro 2: releasing the lock" in cor.res
assert cor.res.find("coro 1: releasing the lock") < cor.res.find("coro 2: holding the lock") or \
cor.res.find("coro 2: releasing the lock") < cor.res.find("coro 1: holding the lock")
        """
