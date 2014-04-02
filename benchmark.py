import time
import logging
import random

from appmetrics import metrics, histogram

log = logging.getLogger("benchmark")

DURATION = 30
MIN_LATENCY = 1
MAX_LATENCY = 15


"""
Microbenchmark used to measure library's overhead.
The benchmark works by emulating a process that gets requests continuously and handles them
with a latency choosen randomly between MIN_LATENCY and MAX_LATENCY milliseconds.
The idea is to emulate some kind of i/o bound worker such as a web worker that uses mostly a db.
"""

def benchmark(new_fun, duration):
    name = "bench"
    new_fun(name)

    work_time = 0.0
    overhead = 0.0

    started_on = time.time()
    while True:
        now = time.time()
        if now - started_on >= duration:
            break

        latency = random.randint(MIN_LATENCY, MAX_LATENCY) / 1000.0
        time.sleep(latency)

        t1 = time.time()
        metrics.notify(name, latency)
        t2 = time.time()
        overhead += (t2 - t1)

        work_time += latency

    elapsed = time.time() - started_on

    metric_value = metrics.get(name)

    metrics.delete_metric(name)

    return elapsed, work_time, overhead, metric_value


def report(kind, duration, work_time, overhead, metric_value):
    overhead_pct = overhead / duration * 100.0
    work_pct = work_time / duration * 100.0

    log.info(
        "%s: %.4fs over %.2fs (%.2fs work, %.2f%%) - %.4f%% with results %s",
        kind, overhead, duration, work_time, work_pct, overhead_pct, metric_value)


def run(kind, new_fun, duration):
    log.info("benchmarking %s for %s seconds", kind, duration)
    res = benchmark(new_fun, duration)
    report(kind, *res)


def benchmark_all():
    run("counter", metrics.new_counter, DURATION)
    run("histogram", metrics.new_histogram, DURATION)
    run(
        "histogram-sliding time window",
        lambda name: metrics.new_histogram(name, histogram.SlidingTimeWindowReservoir(5)),
        DURATION)
    run(
        "histogram-sliding window",
        lambda name: metrics.new_histogram(name, histogram.SlidingWindowReservoir()),
        DURATION)
    run(
        "histogram-exponentially decaying",
        lambda name: metrics.new_histogram(name, histogram.ExponentialDecayingReservoir()),
        DURATION)
    run("meter", metrics.new_meter, DURATION)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    benchmark_all()
