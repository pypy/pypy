import os, struct, socket, errno, subprocess
from rpython.translator.revdb import ancillary
from rpython.translator.revdb.message import *


maxint64 = int(2**63 - 1)


class Breakpoint(Exception):
    def __init__(self, num):
        self.num = num


class ReplayProcess(object):
    """Represent one replaying subprocess.

    It can be either the one started with --revdb-replay, or a fork.
    """

    def __init__(self, pid, control_socket):
        self.pid = pid
        self.control_socket = control_socket

    def _recv_all(self, size):
        pieces = []
        while size > 0:
            data = self.control_socket.recv(size)
            if not data:
                raise EOFError
            size -= len(data)
            pieces.append(data)
        return ''.join(pieces)

    def send(self, msg):
        binary = struct.pack("iIqqq", msg.cmd, len(msg.extra),
                             msg.arg1, msg.arg2, msg.arg3)
        self.control_socket.sendall(binary + msg.extra)

    def recv(self):
        binary = self._recv_all(struct.calcsize("iIqqq"))
        cmd, size, arg1, arg2, arg3 = struct.unpack("iIqqq", binary)
        extra = self._recv_all(size)
        return Message(cmd, arg1, arg2, arg3, extra)

    def expect(self, cmd, arg1=0, arg2=0, arg3=0, extra=""):
        msg = self.recv()
        assert msg.cmd == cmd
        if arg1 is not Ellipsis:
            assert msg.arg1 == arg1
        if arg2 is not Ellipsis:
            assert msg.arg2 == arg2
        if arg3 is not Ellipsis:
            assert msg.arg3 == arg3
        if extra is not Ellipsis:
            assert msg.extra == extra
        return msg

    def update_times(self, msg):
        self.current_time = msg.arg1
        self.currently_created_objects = msg.arg2

    def clone(self):
        """Fork this subprocess.  Returns a new ReplayProcess() that is
        an identical copy.
        """
        self.send(Message(CMD_FORK))
        s1, s2 = socket.socketpair()
        ancillary.send_fds(self.control_socket.fileno(), [s2.fileno()])
        s2.close()
        msg = self.expect(ANSWER_FORKED, Ellipsis, Ellipsis, Ellipsis)
        self.update_times(msg)
        child_pid = msg.arg3
        other = ReplayProcess(child_pid, s1)
        other.update_times(msg)
        return other

    def close(self):
        """Close this subprocess."""
        try:
            self.send(Message(CMD_QUIT))
        except socket.error:
            pass

    def forward(self, steps):
        """Move this subprocess forward in time."""
        self.send(Message(CMD_FORWARD, steps))
        #
        msg = self.recv()
        if msg.cmd == ANSWER_BREAKPOINT:
            bkpt_num = msg.arg3
            msg = self.recv()
        else:
            bkpt_num = None
        assert msg.cmd == ANSWER_STD
        self.update_times(msg)
        #
        if bkpt_num is not None:
            raise Breakpoint(bkpt_num)
        return msg

    def print_text_answer(self):
        while True:
            msg = self.recv()
            if msg.cmd == ANSWER_TEXT:
                print msg.extra
            elif msg.cmd == ANSWER_STD:
                self.update_times(msg)
                break
            else:
                print >> sys.stderr, "unexpected message %d" % (msg.cmd,)


class ReplayProcessGroup(object):
    """Handle a family of subprocesses.
    """
    MAX_SUBPROCESSES = 31       # maximum number of subprocesses
    STEP_RATIO = 0.25           # subprocess n is between subprocess n-1
                                #   and the end, at this fraction of interval

    def __init__(self, executable, revdb_log_filename):
        s1, s2 = socket.socketpair()
        initial_subproc = subprocess.Popen(
            [executable, '--revdb-replay', revdb_log_filename,
             str(s2.fileno())])
        s2.close()
        child = ReplayProcess(initial_subproc.pid, s1)
        msg = child.expect(ANSWER_INIT, INIT_VERSION_NUMBER, Ellipsis)
        self.total_stop_points = msg.arg2
        msg = child.expect(ANSWER_STD, 1, Ellipsis)
        child.update_times(msg)

        self.active = child
        self.paused = {1: child.clone()}     # {time: subprocess}

    def get_current_time(self):
        return self.active.current_time

    def _check_current_time(self, time):
        assert self.get_current_time() == time
        self.active.send(Message(CMD_FORWARD, 0))
        return self.active.expect(ANSWER_STD, time, Ellipsis)

    def get_max_time(self):
        return self.total_stop_points

    def get_next_clone_time(self):
        if len(self.paused) >= self.MAX_SUBPROCESSES:
            next_time = self.total_stop_points + 1
        else:
            latest_done = max(self.paused)
            range_not_done = self.total_stop_points - latest_done
            next_time = latest_done + int(self.STEP_RATIO * range_not_done) + 1
        return next_time

    def go_forward(self, steps):
        """Go forward, for the given number of 'steps' of time.

        If needed, it will leave clones at intermediate times.
        Does not close the active subprocess.
        """
        assert steps >= 0
        while True:
            cur_time = self.get_current_time()
            if cur_time + steps > self.total_stop_points:
                steps = self.total_stop_points - cur_time
            next_clone = self.get_next_clone_time()
            rel_next_clone = next_clone - cur_time
            if rel_next_clone > steps:
                break
            assert rel_next_clone >= 0
            if rel_next_clone > 0:
                self.active.forward(rel_next_clone)
                steps -= rel_next_clone
            clone = self.active.clone()
            self.paused[clone.current_time] = clone
        self.active.forward(steps)

    def _resume(self, from_time):
        clone_me = self.paused[from_time]
        self.active.close()
        self.active = clone_me.clone()

    def jump_in_time(self, target_time):
        """Jump in time at the given 'target_time'.

        This function always closes the active subprocess.
        """
        if target_time < 1:
            target_time = 1
        if target_time > self.total_stop_points:
            target_time = self.total_stop_points
        self._resume(max(time for time in self.paused if time <= target_time))
        self.go_forward(target_time - self.get_current_time())

    def close(self):
        """Close all subprocesses.
        """
        for subp in [self.active] + self.paused.values():
            subp.close()

    def print_cmd(self, expression):
        """Print an expression.
        """
        self.active.send(Message(CMD_PRINT, extra=expression))
        self.active.print_text_answer()

    def show_backtrace(self):
        """Show the backtrace.
        """
        self.active.send(Message(CMD_BACKTRACE))
        self.active.print_text_answer()
