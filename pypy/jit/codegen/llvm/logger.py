import py, os
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.codegen.llvm.conftest import option


PRINT_DEBUG = option.print_debug


class Logger:
    
    enabled = True
    log_fd = -1

    def _freeze_(self):
        # reset the machine_code_dumper global instance to its default state
        if self.log_fd >= 0:
            os.close(self.log_fd)
            self.__dict__.clear()
        return False
                                                    
    def open(self):
        if not self.enabled:
            return False
        if self.log_fd < 0:
            # check the environment for a file name
            s = os.environ.get('PYPYJITLOG')
            if not s:
                self.enabled = False
                return False
            try:
                flags = os.O_WRONLY|os.O_CREAT|os.O_TRUNC
                self.log_fd = os.open(s, flags, 0666)
            except OSError:
                os.write(2, "could not create log file\n")
                self.enabled = False
                return False
            # log the executable name
            from pypy.jit.codegen.hlinfo import highleveljitinfo
            if highleveljitinfo.sys_executable:
                os.write(self.log_fd, 'SYS_EXECUTABLE %s\n' % (
                    highleveljitinfo.sys_executable,))
        return True

    def dump(self, s):
        if not self.open():
            return
        os.write(self.log_fd, str(s) + '\n')

logger = Logger()


def log(s):
    if PRINT_DEBUG and not we_are_translated():
        print str(s)
    logger.dump(s)
