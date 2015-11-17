#!/usr/bin/env python
import matplotlib
import sys
matplotlib.use('gtkagg')

args = None
import matplotlib.pyplot as plt

import print_stm_log as psl


########## DRAWING STUFF ##########

BOX_HEIGHT = 0.8
PADDING = 0.1
HALF_HEIGHT = BOX_HEIGHT / 2
QUARTER_HEIGHT = HALF_HEIGHT / 2


def plot_boxes(boxes, y, ax):
    coords, colors = [], []
    for x, w, style, i in boxes:
        coords.append((x, w))
        c = STYLES[0][style]
        colors.append(c)
    #
    bars = ax.broken_barh(coords, (y + PADDING, BOX_HEIGHT),
                          facecolors=colors, lw=1, edgecolor=(0, 0, 0),
                          picker=True, antialiased=False, rasterized=True)
    #
    bars.boxes = boxes


__offset = 0
def plot_hlines(hlines, y, ax):
    global __offset
    args = []
    for x1, x2, style in hlines:
        arg = [[x1, x2],
               2*[y + 2*PADDING + __offset * QUARTER_HEIGHT],
               STYLES[1][style]]
        args.extend(arg)
        __offset = (__offset + 1) % 4

    ax.plot(*args, linewidth=10, antialiased=False, rasterized=True,
            solid_capstyle='butt')

def make_legend(ax):
    import matplotlib.patches as mpatch
    import matplotlib.lines as mlines
    boxes, hlines = STYLES
    items, labels = [], []
    for label, color in boxes.items():
        items.append(mpatch.Rectangle((0, 0), 1, 1, fc=color))
        labels.append(label)
    for label, color in hlines.items():
        # items.append(mpatch.Rectangle((0, 0), 1, 1, fc=color))
        if len(color) < 4:
            color = color[0] # e.g. "m-"
        items.append(mlines.Line2D((0, 1), (0, 0), linewidth=10, color=color))
        labels.append(label)
    ax.legend(items, labels)


####################################


def add_box(boxes, x1, x2, color, info):
    boxes.append((x1, x2-x1, color, info))


def add_hline(hlines, x1, x2, color):
    hlines.append((x1, x2, color))


STYLES = [{'becoming inevitable':'b',
           'inevitable':'orange',
           'normal tx':'g',
           'aborted tx':'r'},
          {'paused/waiting':'darkred',
           'major gc':'m-'}]
def add_transaction(boxes, hlines, tr):
    # get the values:
    inited, inevitabled, ended, aborted, pauses, gcs, info = (
        tr.start_time, tr.inevitabled,
        tr.stop_time,
        tr.aborted, tr.pauses, tr.gcs,
        "\n".join(tr.info))
    assert inited is not None

    if inevitabled is not None and not aborted:
        # we may still be "aborted" if we aborted when
        # we tried to become inevitable (XXX)
        add_box(boxes, inited, inevitabled,
                'becoming inevitable', info)
        add_box(boxes, inevitabled, ended,
                'inevitable', info)
    elif not aborted:
        add_box(boxes, inited, ended,
                'normal tx', info)
    else:
        add_box(boxes, inited, ended,
                'aborted tx', info)

    for start, end in pauses:
        if start == end:
            print "Warning, start and end of pause match"
        add_hline(hlines, start, end,
                  'paused/waiting')

    for start, end in gcs:
        if start == end:
            print "Warning, start and end of GC match"
        add_hline(hlines, start, end,
                  'major gc')


class Transaction(object):
    def __init__(self, thread_num, start_time):
        self.thread_num = thread_num
        self.start_time = start_time
        self.stop_time = 0
        self.aborted = False
        self.pauses = []
        self.gcs = []
        self.info = []
        self.inevitabled = None



def transaction_start(curr_trs, entry):
    if entry.threadnum in curr_trs:
        print "WARNING: Start of transaction while there is one already running"
    curr_trs[entry.threadnum] = Transaction(entry.threadnum, entry.timestamp)

def transaction_become_inevitable(curr_trs, entry):
    tr = curr_trs.get(entry.threadnum)
    if tr is not None:
        tr.inevitabled = entry.timestamp

def transaction_commit(curr_trs, finished_trs, entry):
    th_num = entry.threadnum
    tr = curr_trs.get(th_num)
    if tr is not None:
        tr.stop_time = entry.timestamp
        xs = finished_trs.setdefault(th_num, [])
        xs.append(curr_trs[th_num])
        del curr_trs[th_num]


def plot_log(logentries, ax):
    curr_trs = {}
    finished_trs = {}
    for entry in logentries:
        th_num = entry.threadnum

        if entry.event == psl.STM_TRANSACTION_START:
            transaction_start(curr_trs, entry)
        elif entry.event == psl.STM_TRANSACTION_DETACH:
            transaction_commit(curr_trs, finished_trs, entry)
        elif (entry.event == psl.STM_TRANSACTION_REATTACH
              or (entry.event == psl.STM_GC_MINOR_START
                  and curr_trs.get(th_num) is None)):
            # minor GC is approximate fix for JIT not emitting REATTACH
            # in certain situations:
            transaction_start(curr_trs, entry)
            transaction_become_inevitable(curr_trs, entry)
        elif entry.event == psl.STM_TRANSACTION_COMMIT:
            transaction_commit(curr_trs, finished_trs, entry)
        elif entry.event == psl.STM_BECOME_INEVITABLE:
            transaction_become_inevitable(curr_trs, entry)
        elif entry.event == psl.STM_TRANSACTION_ABORT:
            tr = curr_trs.get(th_num)
            if tr is not None:
                tr.stop_time = entry.timestamp
                tr.aborted = True
                xs = finished_trs.setdefault(th_num, [])
                xs.append(curr_trs[th_num])
                del curr_trs[th_num]
        elif entry.event in (psl.STM_WAIT_FREE_SEGMENT,
                             psl.STM_WAIT_SYNCING,
                             psl.STM_WAIT_SYNC_PAUSE,
                             psl.STM_WAIT_OTHER_INEVITABLE):
            tr = curr_trs.get(th_num)
            if tr is not None:
                tr.pauses.append((entry.timestamp, entry.timestamp))
        elif entry.event == psl.STM_WAIT_DONE:
            tr = curr_trs.get(th_num)
            if tr is not None:
                tr.pauses[-1] = (tr.pauses[-1][0], entry.timestamp)
        elif entry.event in (psl.STM_GC_MAJOR_START,): # no minor
            tr = curr_trs.get(th_num)
            if tr is not None:
                tr.gcs.append((entry.timestamp, entry.timestamp))
        elif entry.event in (psl.STM_GC_MAJOR_DONE,):
            tr = curr_trs.get(th_num)
            if tr is not None:
                tr.gcs[-1] = (tr.gcs[-1][0], entry.timestamp)

        # attach logentry as clickable transaction info
        tr = curr_trs.get(th_num)
        if tr is None:
            # no current transaction
            # try to attach it to the last transaction
            tr = finished_trs.get(th_num, [None])[-1]
        if tr is not None:
            tr.info.append(str(entry))
        # # also affects other transaction:
        # if entry.marker2:
        #     tr2 = curr_trs.get(entry.otherthreadnum)
        #     if tr2 is None:
        #         tr2 = finished_trs.get(entry.otherthreadnum, [None])[-1]
        #     if tr2 is not None:
        #         tr2.info.append(str(entry))




    # plt.ion()
    for th_num, trs in finished_trs.items():
        # plt.draw()
        # plt.show()
        print "Thread", th_num
        print "> Transactions:", len(trs)

        boxes = []
        hlines = []
        for tr in trs:
            add_transaction(boxes, hlines, tr)

        plot_boxes(boxes, th_num, ax)
        plot_hlines(hlines, th_num, ax)
        make_legend(ax)
        print "> Pauses:", len(hlines)

    # plt.ioff()

    return finished_trs


def onpick(event):
    if hasattr(event.artist, "info"):
        print "== pick ==\n", event.artist.info
    if hasattr(event.artist, "boxes"):
        x = event.mouseevent.xdata
        for x1, w, c, i in event.artist.boxes:
            if x >= x1 and x <= x1+w:
                print "== pick ==\n", i
                break
        else:
            print "== pick ==\nCould not find info"




def plot(logentries):
    global fig

    print "Draw..."
    fig = plt.figure()
    grid_spec = matplotlib.gridspec.GridSpec(1, 1)
    axs = [fig.add_subplot(grid_spec[0])]

    trs = plot_log(logentries, axs[0])

    thread_count = len(trs)

    axs[0].set_ylabel("Thread")
    axs[0].set_ylim(0, thread_count+2)
    axs[0].set_yticks([r+0.5 for r in range(thread_count+1)])
    axs[0].set_yticklabels(range(thread_count+1))
    #axs[0].set_xticks([])
    print "Drawn."

    axs[0].set_xlabel("Runtime [s]")

    # adjust labels:
    first_trs = [th[0].start_time for th in trs.values()]
    last_trs = [th[-1].stop_time for th in trs.values()]
    start_time, stop_time = min(first_trs), max(last_trs)
    offset = (stop_time - start_time) * 0.1
    axs[0].set_xlim((start_time - offset, stop_time + offset))

    def label_format(x, pos):
        return "%.2f" % (x - start_time)
    major_formatter = matplotlib.ticker.FuncFormatter(label_format)
    axs[0].xaxis.set_major_formatter(major_formatter)

    # event connect
    fig.canvas.mpl_connect('pick_event', onpick)

    plt.draw()
    plt.show()

# ____________________________________________________________

def main(argv):
    assert len(argv) == 1, "expected a filename argument"
    plot(psl.parse_log(argv[0]))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
