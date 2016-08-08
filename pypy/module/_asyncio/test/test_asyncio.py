class AppTestAsyncIO(object):
    
    spaceconfig = dict(usemodules=["select","_socket","thread","signal","struct","_multiprocessing","array","_posixsubprocess","fcntl","unicodedata"])
    
    def test_gil_issue(self):
        # the problem occured at await asyncio.open_connection after calling run_until_complete
        """
        import encodings.idna
        import asyncio
        async def f():
            reader, writer = await asyncio.open_connection('example.com', 80)
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(f())"""
