import sys, os, struct, socket, errno, subprocess
from rpython.translator.revdb import ancillary
from rpython.translator.revdb.message import *


maxint64 = int(2**63 - 1)


class Breakpoint(Exception):
    def __init__(self, time, num):
        self.time = time
        self.num = num


class ReplayProcess(object):
    """Represent one replaying subprocess.

    It can be either the one started with --revdb-replay, or a fork.
    """

    def __init__(self, pid, control_socket, breakpoints_cache={}):
        self.pid = pid
        self.control_socket = control_socket
        self.tainted = False
        self.breakpoints_cache = breakpoints_cache    # don't change this dict

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

    def expect_ready(self):
        msg = self.expect(ANSWER_READY, Ellipsis, Ellipsis)
        self.update_times(msg)

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
        msg = self.expect(ANSWER_FORKED, Ellipsis)
        child_pid = msg.arg3
        self.expect_ready()
        other = ReplayProcess(child_pid, s1,
                              breakpoints_cache=self.breakpoints_cache)
        other.expect_ready()
        return other

    def close(self):
        """Close this subprocess."""
        try:
            self.send(Message(CMD_QUIT))
        except socket.error:
            pass

    def forward(self, steps, breakpoint_mode='b'):
        """Move this subprocess forward in time.
        Returns the Breakpoint or None.
        """
        assert not self.tainted
        self.send(Message(CMD_FORWARD, steps, ord(breakpoint_mode)))
        #
        # record the first ANSWER_BREAKPOINT, drop the others
        # (in corner cases only could we get more than one)
        bkpt = None
        while True:
            msg = self.recv()
            if msg.cmd != ANSWER_BREAKPOINT:
                break
            if bkpt is None:
                bkpt = Breakpoint(msg.arg1, msg.arg3)
        assert msg.cmd == ANSWER_READY
        self.update_times(msg)
        return bkpt

    def print_text_answer(self):
        while True:
            msg = self.recv()
            if msg.cmd == ANSWER_TEXT:
                sys.stdout.write(msg.extra)
                sys.stdout.flush()
            elif msg.cmd == ANSWER_READY:
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
        child.expect_ready()

        self.active = child
        self.paused = {1: child.clone()}     # {time: subprocess}
        self.breakpoints = {}

    def get_current_time(self):
        return self.active.current_time

    def _check_current_time(self, time):
        assert self.get_current_time() == time
        self.active.send(Message(CMD_FORWARD, 0))
        return self.active.expect(ANSWER_READY, time, Ellipsis)

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

    def is_tainted(self):
        return self.active.tainted

    def go_forward(self, steps, breakpoint_mode='b'):
        """Go forward, for the given number of 'steps' of time.

        If needed, it will leave clones at intermediate times.
        Does not close the active subprocess.  Note that
        is_tainted() must return false in order to use this.

        breakpoint_mode:
          'b' = regular mode where hitting a breakpoint stops
          'i' = ignore breakpoints
          'r' = record the occurrence of a breakpoint but continue
        """
        assert steps >= 0
        self.update_breakpoints()
        latest_bkpt = None
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
                bkpt = self.active.forward(rel_next_clone, breakpoint_mode)
                if breakpoint_mode == 'r':
                    latest_bkpt = bkpt or latest_bkpt
                elif bkpt:
                    raise bkpt
                steps -= rel_next_clone
            clone = self.active.clone()
            self.paused[clone.current_time] = clone
        bkpt = self.active.forward(steps, breakpoint_mode)
        if breakpoint_mode == 'r':
            bkpt = bkpt or latest_bkpt
        if bkpt:
            raise bkpt

    def go_backward(self, steps):
        """Go backward, for the given number of 'steps' of time.

        Closes the active process.  Implemented as jump_in_time()
        and then forward-searching for breakpoint locations (if any).
        """
        assert steps >= 0
        initial_time = self.get_current_time()
        if not self.breakpoints:
            self.jump_in_time(initial_time - steps)
        else:
            self._backward_search_forward(
                search_start_time       = initial_time - 957,
                search_stop_time        = initial_time - 1,
                search_go_on_until_time = initial_time - steps)

    def _backward_search_forward(self, search_start_time, search_stop_time,
                                 search_go_on_until_time=1):
        while True:
            self.jump_in_time(max(search_start_time, search_go_on_until_time))
            search_start_time = self.get_current_time()
            time_range_to_search = search_stop_time - search_start_time
            if time_range_to_search <= 0:
                print "[not found]"
                return
            print "[searching %d..%d]" % (search_start_time,
                                          search_stop_time)
            self.go_forward(time_range_to_search, breakpoint_mode='r')
            # If at least one breakpoint was found, the Breakpoint
            # exception is raised with the *last* such breakpoint.
            # Otherwise, we continue here.  Search farther along a
            # 3-times-bigger range.
            search_stop_time = search_start_time
            search_start_time -= time_range_to_search * 3

    def update_breakpoints(self):
        if self.active.breakpoints_cache != self.breakpoints:
            if self.breakpoints:
                breakpoints = [self.breakpoints.get(n, '')
                               for n in range(max(self.breakpoints) + 1)]
            else:
                breakpoints = []
            extra = '\x00'.join(breakpoints)
            self.active.breakpoints_cache = None
            self.active.send(Message(CMD_BREAKPOINTS, extra=extra))
            self.active.expect_ready()
            self.active.breakpoints_cache = self.breakpoints.copy()

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
        self.go_forward(target_time - self.get_current_time(),
                        breakpoint_mode='i')

    def close(self):
        """Close all subprocesses.
        """
        for subp in [self.active] + self.paused.values():
            subp.close()

    def print_cmd(self, expression):
        """Print an expression.
        """
        self.active.tainted = True
        self.active.send(Message(CMD_PRINT, extra=expression))
        self.active.print_text_answer()

    def show_backtrace(self):
        """Show the backtrace.
        """
        self.active.send(Message(CMD_BACKTRACE))
        self.active.print_text_answer()

    def show_locals(self):
        """Show the locals.
        """
        self.active.send(Message(CMD_LOCALS))
        self.active.print_text_answer()
