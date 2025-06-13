#!/usr/bin/env python3
import sys
import os
import subprocess
import statistics
import random
import argparse

def format_nonzero_fraction(x, n):
    s = f"{x:.20f}".rstrip("0")
    if "." not in s:
        return s

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
    os.remove(path)

    return result


def gen_log_id():
    i = int(random.random())
    return f"log_{i}"


def parse_args():
    parser = argparse.ArgumentParser(
        prog='Measuring the jit summary data'
    )
    parser.add_argument('filename')
    parser.add_argument('-n', '--number', type=int)
    args = parser.parse_args()
    return (args.filename, args.number)

def main():
    log_output = f"{gen_log_id()}.log"
    env = os.environ.copy()
    env["PYPYLOG"] = f"jit-summary:{log_output}"
    env["PYTHONPATH"] = "benchmarks/lib/chameleon/src:benchmarks/lib/dulwich-0.19.13:benchmarks/lib/jinja2:benchmarks/lib/pyxl:benchmarks/lib/monte:benchmarks/lib/pytz:benchmarks/lib/sympy:benchmarks/lib/genshi:benchmarks/lib/mako:benchmarks/lib/sqlalchemy:benchmarks/lib/twisted-trunk/twisted:/benchmarks/lib/genshi"

    target, number = parse_args()
    binarie_w_names = [("pypy-main", "pypy/goal/pypy-c"), ("pypy-jit-ext", "pypy/goal/pypy-jit-ext")]

    print("===> jit-summary Tracing time (s) results")
    for i, (name, bin) in enumerate(binarie_w_names):
        tracing_times = []

        command = [bin, target]
        for _ in range(number):
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
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

        print(f"{i+1}: {bin} {target}")
        print("\t{}\t\t{}\t{}\t\t{}\t\t{}".format("Mean", "Std.Dev.", "Min", "Median", "Max"))
        print("\t{}\t{}\t{}\t{}\t{}".format(mean, format_nonzero_fraction(stdev, 5), mn, median, mx))


if __name__ == '__main__':
    main()
