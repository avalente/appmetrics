from __future__ import print_function

import os
import sys
import time
import random

from appmetrics import metrics, reporter

@metrics.with_histogram("worker_latency")
@metrics.with_meter("worker_throughput")
def worker():
    # just spend some time
    time.sleep(random.random()/10.0)

def main(directory):
    if not os.path.isdir(directory):
        sys.exit("ERROR: {} is not a directory".format(directory))

    # tag the metrics to group them together
    metrics.tag("worker_latency", "worker")
    metrics.tag("worker_throughput", "worker")

    # register a csv reporter that will dump the metrics with the tag "worker" each 2 seconds
    # to csv files in the given directory
    reporter.register(
        reporter.CSVReporter(directory), reporter.fixed_interval_scheduler(2), "worker")

    # emulate some work
    print("Hit CTRL-C to stop the process")
    while True:
        try:
            worker()
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: {} <directory>".format(sys.argv[0]))
    main(sys.argv[1])
