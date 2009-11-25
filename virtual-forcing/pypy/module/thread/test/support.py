import py
import time, gc
from pypy.conftest import gettestobjspace, option
from pypy.interpreter.gateway import ObjSpace, W_Root, interp2app_temp
from pypy.module.thread import gil


NORMAL_TIMEOUT = 300.0   # 5 minutes

def waitfor(space, w_condition, delay=1):
    adaptivedelay = 0.04
    limit = time.time() + delay * NORMAL_TIMEOUT
    while time.time() <= limit:
        gil.before_external_call()
        time.sleep(adaptivedelay)
        gil.after_external_call()
        gc.collect()
        if space.is_true(space.call_function(w_condition)):
            return
        adaptivedelay *= 1.05
    print '*** timed out ***'
waitfor.unwrap_spec = [ObjSpace, W_Root, float]


class GenericTestThread:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('thread', 'time'))
        cls.space = space

        if option.runappdirect:
            def plain_waitfor(condition, delay=1):
                adaptivedelay = 0.04
                limit = time.time() + NORMAL_TIMEOUT * delay
                while time.time() <= limit:
                    time.sleep(adaptivedelay)
                    gc.collect()
                    if condition():
                        return
                    adaptivedelay *= 1.05
                print '*** timed out ***'
                
            cls.w_waitfor = plain_waitfor
        else:
            cls.w_waitfor = space.wrap(interp2app_temp(waitfor))
        cls.w_busywait = space.appexec([], """():
            import time
            return time.sleep
        """)
