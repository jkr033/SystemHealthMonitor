#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime

def cpu_percent(interval=1.0):
    def read():
        with open("/proc/stat") as f:
            fields = [float(x) for x in f.readline().split()[1:]]
        idle = fields[3] + fields[4]
        return idle, sum(fields)

    idle1, total1 = read()
    time.sleep(interval)
    idle2, total2 = read()
    delta = total2 - total1
    return round(100 * (1 -(idle2 - idle1) / delta), 1) if delta else 0.0

def memory_percent():
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, value = line.split(":")
            info[key] = int(value.split()[0])
    used = info["MemTotal"] - info["MemAvailable"]
    return round(100 * used / info["MemTotal"], 1)

def disk_percent(path="/"):
    usage = shutil.disk_usage(path)
    return round(100 * usage.used / usage.total, 1)

def uptime_hours():
    with open("/proc/uptime") as f:
        return round(float(f.read().split()[0]) / 3600, 1)

def collect(disk_path):
    load1, load5, load15 = os.getloadavg()
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "cpu_percent": cpu_percent(),
        "memory_percent": memory_percent(),
        "disk_percent": disk_percent(disk_path),
        "load_1m": round(load1, 2),
        "cpu_cores": os.cpu_count(),
        "uptime_hours": uptime_hours(),
    }

def check(metrics, args):
    warnings = []
    if metrics["cpu_percent"] > args.cpu:
        warnings.append(f"CPU high: {metrics['cpu_percent']}% (limit {args.cpu}%)")
    if metrics["memory_percent"] > args.mem:
        warnings.append(f"Memory high: {metrics['memory_percent']}% (limit {args.mem}%)")
    if metrics["disk_percent"] > args.disk:
        warnings.append(f"Disk high: {metrics['disk_percent']}% (limit {args.disk}%)")
    if metrics["load_1m"] > metrics["cpu_cores"]:
        warnings.append(f"Load average {metrics['load_1m']} exceeds {metrics['cpu_cores']} cores")
    return warnings



def main():
    p = argparse.ArgumentParser(description="Simple Linux health monitor")
    p.add_argument("--cpu", type=float, default=85, help="CPU %% warning threshold")
    p.add_argument("--mem", type=float, default=85, help="Memory %% warning threshold")
    p.add_argument("--disk", type=float, default=90, help="Disk %% warning threshold")
    p.add_argument("--path", default="/", help="Filesystem path to check")
    p.add_argument("--json", action="store_true", help="Print JSON instead of text")
    p.add_argument("--log", metavar="FILE", help="Append a JSON line to FILE")
    args = p.parse_args()

    metrics = collect(args.path)
    warnings = check(metrics, args)
    metrics["status"] = "WARNING" if warnings else "OK"
    metrics["warnings"] = warnings

    if args.json:
        print(json.dumps(metrics, indent=2))
    else:
        print(f"[{metrics['timestamp']}] Status: {metrics['status']}")
        print(f"  CPU     {metrics['cpu_percent']:>5}%")
        print(f"  Memory  {metrics['memory_percent']:>5}%")
        print(f"  Disk    {metrics['disk_percent']:>5}%  ({args.path})")
        print(f"  Load    {metrics['load_1m']} ({metrics['cpu_cores']} cores)")
        print(f"  Uptime  {metrics['uptime_hours']} h")
        for w in warnings:
            print(f"  ! {w}")

    if args.log:
        with open(args.log, "a") as f:
            f.write(json.dumps(metrics) + "\n")

    sys.exit(1 if warnings else 0)


if __name__ == "__main__":
    main()
