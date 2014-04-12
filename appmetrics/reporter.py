##  Module reporter.py
##
##  Copyright (c) 2014 Antonio Valente <y3sman@gmail.com>
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##  http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.

"""
Reporting facilities
"""


import os
import csv
import logging
import uuid
import threading
import time
import atexit

from . import metrics, py3comp


log = logging.getLogger('appmetrics.reporter')


REGISTRY = {}
LOCK = threading.Lock()


def register(callback, schedule, tag=None):
    """
    Register a callback which will be called at scheduled intervals with
    the metrics that have the given tag (or all the metrics if None).
    Return an identifier which can be used to access the registered callback later.
    """

    try:
        iter(schedule)
    except TypeError:
        raise TypeError("{} is not iterable".format(schedule))

    if not callable(callback):
        raise TypeError("{} is not callable".format(callback))

    thread = Timer(schedule, callback, tag)

    id_ = str(uuid.uuid4())
    with LOCK:
        REGISTRY[id_] = thread

    thread.start()

    return id_


def get(id_):
    """
    Return the registered callback with the given name, or None if it does not exist
    """
    return REGISTRY.get(id_)


def remove(id_):
    """
    Remove the callback and its schedule
    """
    with LOCK:
        thread = REGISTRY.pop(id_, None)
        if thread is not None:
            thread.cancel()

    return thread


class Timer(threading.Thread):
    """
    Encapsulate a callback and its parameters
    """

    def __init__(self, schedule, callback, tag=None):
        """
        "schedule" must be an iterator yielding the next "tick" at each iteration
        """
        super(Timer, self).__init__()

        self.schedule = schedule
        self.callback = callback
        self.tag = tag
        self._event = threading.Event()
        self.daemon = True

    def run(self):
        while not self._event.is_set():
            now = time.time()
            # skip already passed ticks
            for next_time in self.schedule:
                if next_time > now:
                    break
            # the iterator was consumed, exit
            else:
                break

            # sleep for the remaining time
            time.sleep(next_time - now)

            # the event may have been set while sleeping
            if not self._event.is_set():
                data = get_metrics(self.tag)

                if not data:
                    log.debug("No metrics found for tag: {}".format(self.tag))
                else:
                    # call the function, finally
                    self.callback(data)

        # set the event, for consistency
        self.cancel()

    def cancel(self):
        """
        Cancel the timer, no more actions will be performed
        """
        self._event.set()

    @property
    def is_running(self):
        return not self._event.is_set()


def get_metrics(tag):
    """
    Return the values for the metrics with the given tag or all the available metrics if None
    """
    if tag is None:
        return metrics.metrics_by_name_list(metrics.metrics())
    else:
        return metrics.metrics_by_tag(tag)


def fixed_interval_scheduler(interval):
    """
    A scheduler that ticks at fixed intervals of "interval" seconds
    """
    start = time.time()
    next_tick = start

    while True:
        next_tick += interval
        yield next_tick


class CSVReporter(object):
    histogram_header = (
        'time', 'n', 'min', 'max', 'arithmetic_mean', 'median', 'harmonic_mean', 'geometric_mean',
        'standard_deviation', 'variance', 'percentile_50', 'percentile_75', 'percentile_90',
        'percentile_95', 'percentile_99', 'percentile_99.9', 'kurtosis', 'skewness')

    meter_header = ('time', 'count', 'mean', 'one', 'five', 'fifteen', 'day')

    def __init__(self, directory):
        self.directory = directory

    def file_name(self, name, kind):
        file_name = os.path.join(self.directory, "{}_{}.csv".format(name, kind))

        if not os.path.exists(file_name):
            new = True
        else:
            new = False

        return file_name, new

    def dump_histogram(self, name, obj):

        # histogram doesn't fit into a tabular format
        obj.pop('histogram')

        # we already know its kind
        kind = obj.pop('kind')

        # flatten percentiles
        percentiles = obj.pop('percentile')
        for k, v in percentiles:
            obj['percentile_{}'.format(k)] = v

        # add the current time
        obj['time'] = time.time()

        file_name, new = self.file_name(name, kind)

        with open(file_name, "a" if py3comp.PY3 else "ab") as of:
            writer = csv.DictWriter(of, self.histogram_header)

            # if the file is new, write the header once
            if new:
                writer.writerow(dict(zip(self.histogram_header, self.histogram_header)))

            writer.writerow(obj)

        return file_name

    def dump_meter(self, name, obj):

        # we already know its kind
        kind = obj.pop('kind')

        # add the current time
        obj['time'] = time.time()

        file_name, new = self.file_name(name, kind)

        with open(file_name, "a" if py3comp.PY3 else "ab") as of:
            writer = csv.DictWriter(of, self.meter_header)

            # if the file is new, write the header once
            if new:
                writer.writerow(dict(zip(self.meter_header, self.meter_header)))

            writer.writerow(obj)

        return file_name

    def __call__(self, objects):
        for name, obj in py3comp.iteritems(objects):
            fun = getattr(self, "dump_%s" % obj.get('kind', "unknown"), None)
            if fun:
                # protect the original object
                fun(name, obj.copy())


@atexit.register
def cleanup():
    for v in REGISTRY.values():
        v.cancel()
