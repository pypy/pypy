#!/usr/bin/env python3
import sys
import os
import subprocess
import statistics

def format_nonzero_fraction(x, n):
    s = f"{x:.20f}".rstrip("0")  # 十分な桁数で文字列化して末尾の0は削除
    if "." not in s:
        return s  # 小数点がない場合（整数）はそのまま

    int_part, frac_part = s.split(".")

    count = 0
    result_frac = ""
    for c in frac_part:
        result_frac += c
        if c != "0":
            count += 1
        if count == n:
            break

    return f"{int_part}.{result_frac}" if result_frac else int_part

def parse_jit_summary(path):
    result = dict()
    with open(path) as f:
        while True:
            line = f.readline().rstrip()
            if not line:
                break
            if line.startswith("Tracing:"):
                items = line.split('\t')
                time = float(items[-1])
                result["Tracing"] = time

    return result

i = -1

def gen_log_id():
    global i
    i += 1
    return f"log_{i}"

log_output = f"{gen_log_id()}.log"
env = os.environ.copy()
env["PYPYLOG"] = f"jit-summary:{log_output}"

argv = sys.argv
if len(argv) < 3:
    exit(1)

number = int(argv[1])
bin = argv[2]
target = argv[3]

tracing_times = []

command = [bin, target]
for _ in range(number):
    subprocess.run(
        command,
        env=env
    )
    r = parse_jit_summary(log_output)
    tracing_times.append(r["Tracing"])

# mean, std.dev., min., median, max
mean = statistics.mean(tracing_times)
stdev = statistics.stdev(tracing_times)
mn = min(tracing_times)
mx = max(tracing_times)
median = statistics.median(tracing_times)

print("===> jit-summary Tracing time (s) results")
print("\t{}\t\t{}\t{}\t\t{}\t\t{}".format("Mean", "Std.Dev.", "Min", "Median", "Max"))
print("\t{}\t{}\t{}\t{}\t{}".format(mean, format_nonzero_fraction(stdev, 5), mn, median, mx))
