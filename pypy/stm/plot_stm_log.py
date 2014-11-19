#!/usr/bin/env python
import matplotlib
import sys
matplotlib.use('gtkagg')

args = None
import matplotlib.pyplot as plt

import print_stm_log as psl


########## DRAWING STUFF ##########

BOX_HEIGHT = 0.8
HALF_HEIGHT = 0.1 + BOX_HEIGHT / 2
QUARTER_HEIGHT = 0.1 + BOX_HEIGHT / 4


def plot_boxes(boxes, y, ax):
    coords = [(x, w) for x, w, c, i in boxes]
    colors = [c for x, w, c, i in boxes]
    bars = ax.broken_barh(coords, (y+0.1, BOX_HEIGHT),
                          facecolors=colors, lw=1, edgecolor=(0, 0, 0),
                          picker=True, antialiased=False, rasterized=True)

    bars.boxes = boxes


def plot_hlines(hlines, y, ax):
    args = [[[x1, x2], [y+HALF_HEIGHT, y+HALF_HEIGHT], color] for
            x1, x2, color in hlines]
    # flatten:
    args = [item for sublist in args for item in sublist]
    ax.plot(*args, linewidth=5, antialiased=False, rasterized=True)


####################################


def add_box(boxes, x1, x2, color, info):
    boxes.append((x1, x2-x1, color, info))


def add_hline(hlines, x1, x2, color):
    hlines.append((x1, x2, color))


def add_transaction(boxes, hlines, inited, inevitabled,
                    ended, aborted, pauses, info=""):
    assert inited is not None

    if inevitabled is not None:
        add_box(boxes, inited, inevitabled, 'b', info)
        add_box(boxes, inevitabled, ended, 'orange', info)
    elif not aborted:
        add_box(boxes, inited, ended, 'g', info)
    else:
        add_box(boxes, inited, ended, 'r', info)

    for start, end in pauses:
        add_hline(hlines, start, end, 'magenta')


class Transaction(object):
    def __init__(self, thread_num, start_time):
        self.thread_num = thread_num
        self.start_time = start_time
        self.stop_time = 0
        self.aborted = False
        self.pauses = []
        self.info = []


def plot_log(logentries, ax):
    curr_trs = {}
    finished_trs = {}
    for entry in logentries:
        th_num = entry.threadnum

        if entry.event == psl.STM_TRANSACTION_START:
            if th_num in curr_trs:
                print "WARNING: Start of transaction while there is one already running"
            curr_trs[th_num] = Transaction(th_num, entry.timestamp)
        elif entry.event == psl.STM_TRANSACTION_COMMIT:
            tr = curr_trs.get(th_num)
            if tr is not None:
                tr.stop_time = entry.timestamp
                xs = finished_trs.setdefault(th_num, [])
                xs.append(curr_trs[th_num])
                del curr_trs[th_num]
        elif entry.event == psl.STM_TRANSACTION_ABORT:
            tr = curr_trs.get(th_num)
            if tr is not None:
                tr.stop_time = entry.timestamp
                tr.aborted = True
                xs = finished_trs.setdefault(th_num, [])
                xs.append(curr_trs[th_num])
                del curr_trs[th_num]
        elif entry.event in (psl.STM_WAIT_SYNC_PAUSE, psl.STM_WAIT_CONTENTION,
                             psl.STM_WAIT_FREE_SEGMENT):
            tr = curr_trs.get(th_num)
            if tr is not None:
                tr.pauses.append((entry.timestamp, entry.timestamp))
        elif entry.event == psl.STM_WAIT_DONE:
            tr = curr_trs.get(th_num)
            if tr is not None:
                tr.pauses[-1] = (tr.pauses[-1][0], entry.timestamp)


        # attach logentry as transaction info
        tr = curr_trs.get(th_num)
        if tr is not None:
            tr.info.append(str(entry))
        if entry.event in (psl.STM_ABORTING_OTHER_CONTENTION,):
            tr2 = curr_trs.get(entry.otherthreadnum)
            if tr2 is not None:
                tr2.info.append(str(entry))



    # plt.ion()
    for th_num, trs in finished_trs.items():
        # plt.draw()
        # plt.show()
        print "Thread", th_num
        print "> Transactions:", len(trs)

        boxes = []
        hlines = []
        for tr in trs:
            add_transaction(boxes, hlines,
                            tr.start_time, None, tr.stop_time,
                            tr.aborted, tr.pauses,
                            "\n".join(tr.info))
        plot_boxes(boxes, th_num, ax)
        plot_hlines(hlines, th_num, ax)
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
    axs[0].set_ylim(0, thread_count)
    axs[0].set_yticks([r+0.5 for r in range(thread_count)])
    axs[0].set_yticklabels(range(thread_count))
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
