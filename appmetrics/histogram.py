##  Module histogram.py
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

import collections
import random
import threading
import abc
import time
import operator
import math

from . import statistics, exceptions, py3comp


DEFAULT_UNIFORM_RESERVOIR_SIZE = 1028
DEFAULT_TIME_WINDOW_SIZE = 60
DEFAULT_EXPONENTIAL_DECAY_FACTOR = 0.015


def search_greater(values, target):
    """
    Return the first index for which target is greater or equal to the first item of the tuple found in values
    """
    first = 0
    last = len(values)

    while first < last:
        middle = (first+last)//2
        if values[middle][0] < target:
            first = middle+1
        else:
            last = middle

    return first


class ReservoirBase(object):
    __metaclass__ = abc.ABCMeta

    """
    Base class for reservoirs. Subclass and override _do_add, _get_values and _same_parameters
    """

    def add(self, value):
        """
        Add a value to the reservoir
        The value will be casted to a floating-point, so a TypeError or a ValueError may be raised.
        """

        if not isinstance(value, float):
            value = float(value)

        return self._do_add(value)

    @property
    def values(self):
        """
        Return the stored values
        """

        return self._get_values()


    @property
    def sorted_values(self):
        """
        Sort and return the current sample values
        """

        return sorted(self.values)

    def same_kind(self, other):
        """
        Return True if "other" is an object of the same type and it was instantiated with the same parameters
        """

        return type(self) is type(other) and self._same_parameters(other)

    @abc.abstractmethod
    def _do_add(self, value):
        """
        Add the floating-point value to the reservoir. Override in subclasses
        """

    @abc.abstractmethod
    def _get_values(self):
        """
        Get the current reservoir's content. Override in subclasses
        """

    @abc.abstractmethod
    def _same_parameters(self, other):
        """
        Return True if this object has been instantiated with the same parameters as "other".
        Override in subclasses
        """


class UniformReservoir(ReservoirBase):
    """
    A random sampling reservoir of floating-point values. Uses Vitter's Algorithm R to produce a statistically
    representative sample (http://www.cs.umd.edu/~samir/498/vitter.pdf)
    """

    def __init__(self, size=DEFAULT_UNIFORM_RESERVOIR_SIZE):
        self.size = size
        self._values = [0] * size
        self.count = 0
        self.lock = threading.Lock()

    def _do_add(self, value):
        changed = False

        with self.lock:
            if self.count < self.size:
                self._values[self.count] = value
                changed = True
            else:
                # not randint() because it yields different values on python 3, it
                # would be a nightmare to test.
                k = int(random.uniform(0, self.count))
                if k < self.size:
                    self._values[k] = value
                    changed = True

            self.count += 1

        return changed

    def _get_values(self):
        return self._values[:min(self.count, self.size)]

    def _same_parameters(self, other):
        return self.size == other.size

    def __repr__(self):
        return "{}({})".format(type(self).__name__, self.size)


class SlidingWindowReservoir(ReservoirBase):
    """
    A simple sliding-window reservoir that keeps the last N values
    """

    def __init__(self, size=DEFAULT_UNIFORM_RESERVOIR_SIZE):
        self.size = size
        self.deque = collections.deque(maxlen=self.size)

    def _do_add(self, value):
        # No need for explicit lock - deques should be thread-safe:
        # http://docs.python.org/2/library/collections.html#collections.deque
        self.deque.append(value)

    def _get_values(self):
        return list(self.deque)

    def _same_parameters(self, other):
        return self.size == other.size

    def __repr__(self):
        return "{}({})".format(type(self).__name__, self.size)


class SlidingTimeWindowReservoir(ReservoirBase):
    """
    A time-sliced reservoir that keeps the values added in the last N seconds
    """

    def __init__(self, window_size=DEFAULT_TIME_WINDOW_SIZE):
        """
        Build a new sliding time-window reservoir
        window_size is the time window size in seconds
        """
        self.window_size = window_size
        self.lock = threading.Lock()
        self.key = operator.itemgetter(0)
        self._values = []

    def _do_add(self, value):
        now = time.time()

        with self.lock:
            self.tick(now)

        self._values.append((now, value))

    def tick(self, now):
        target = now - self.window_size

        # the values are sorted by the first element (timestamp), so let's perform a dichotomic search
        idx = search_greater(self._values, target)

        # older values found, discard them
        if idx:
            self._values = self._values[idx:]

    def _get_values(self):
        now = time.time()

        with self.lock:
            self.tick(now)

        return [y for x, y in self._values]

    def _same_parameters(self, other):
        return self.window_size == other.window_size

    def __repr__(self):
        return "{}({})".format(type(self).__name__, self.window_size)


class ExponentialDecayingReservoir(ReservoirBase):
    """
    An exponential-weighted reservoir which exponentially decays older values
    in order to give greater significance to newer ones.
    See http://dimacs.rutgers.edu/~graham/pubs/papers/fwddecay.pdf
    """

    #TODO: replace the sort()s with a proper data structure (btree/skiplist). However, since the list
    # is keep sorted (and it should be very small), the sort() shouldn't dramatically slow down
    # the insertions, also considering that the search can be log(n) in that way

    RESCALE_THRESHOLD = 3600
    EPSILON = 1e-12

    def __init__(self, size=DEFAULT_UNIFORM_RESERVOIR_SIZE, alpha=DEFAULT_EXPONENTIAL_DECAY_FACTOR):
        self.size = size
        self.alpha = alpha
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.count = 0
        self.next_scale_time = self.start_time + self.RESCALE_THRESHOLD
        self.key = operator.itemgetter(0)

        self._values = []

    def _lookup(self, timestamp):
        """
        Return the index of the value associated with "timestamp" if any, else None.
        Since the timestamps are floating-point values, they are considered equal if their absolute
        difference is smaller than self.EPSILON
        """

        idx = search_greater(self._values, timestamp)
        if idx < len(self._values) and math.fabs(self._values[idx][0] - timestamp) < self.EPSILON:
            return idx
        return None

    def _put(self, timestamp, value):
        """Replace the value associated with "timestamp" or add the new value"""

        idx = self._lookup(timestamp)
        if idx is not None:
            self._values[idx] = (timestamp, value)
        else:
            self._values.append((timestamp, value))

    def _do_add(self, value):
        now = time.time()

        self.rescale(now)

        rnd = random.random()
        weighted_time = self.weight(now-self.start_time) / rnd

        changed = False

        with self.lock:
            if self.count < self.size:
                self._put(weighted_time, value)
                self._values.sort(key=self.key)
                changed = True
            else:
                first = self._values[0][0]
                if first < weighted_time:
                    idx = self._lookup(weighted_time)
                    if idx is None:
                        self._values[0] = (weighted_time, value)
                        self._values.sort(key=self.key)
                        changed = True

            self.count += 1

        return changed

    def weight(self, t):
        return math.exp(self.alpha * t)

    def rescale(self, now):
        with self.lock:
            if now > self.next_scale_time:
                original_values = self._values[:]
                self._values = []
                for i, (k, v) in enumerate(original_values):
                    k *= math.exp(-self.alpha * (now-self.start_time))
                    self._put(k, v)

                self.count = len(self._values)
                self.start_time = now
                self.next_scale_time = self.start_time + self.RESCALE_THRESHOLD


    def _get_values(self):
        return [y for x, y in self._values[:max(self.count, self.size)]]

    def _same_parameters(self, other):
        return self.size == other.size and self.alpha == other.alpha

    def __repr__(self):
        return "{}({}, {})".format(type(self).__name__, self.size, self.alpha)


class Histogram(object):
    """A metric which calculates some statistics over the distribution of some values"""

    def __init__(self, reservoir):
        self.reservoir = reservoir

    def notify(self, value):
        """Add a new value to the metric"""

        return self.reservoir.add(value)

    def raw_data(self):
        """Return the raw underlying data"""

        return self.reservoir.values

    def get(self):
        """Return the computed statistics over the gathered data"""

        values = self.reservoir.sorted_values

        def safe(f, *args):
            try:
                return f(values, *args)
            except exceptions.StatisticsError:
                return 0.0

        plevels = [50, 75, 90, 95, 99, 99.9]
        percentiles = [safe(statistics.percentile, p) for p in plevels]

        try:
            histogram = statistics.get_histogram(values)
        except exceptions.StatisticsError:
            histogram = [(0, 0)]

        res = dict(
            kind="histogram",
            min=values[0] if values else 0,
            max=values[-1] if values else 0,
            arithmetic_mean=safe(statistics.mean),
            geometric_mean=safe(statistics.geometric_mean),
            harmonic_mean=safe(statistics.harmonic_mean),
            median=safe(statistics.median),
            variance=safe(statistics.variance),
            standard_deviation=safe(statistics.stdev),
            skewness=safe(statistics.skewness),
            kurtosis=safe(statistics.kurtosis),
            percentile=py3comp.zip(plevels, percentiles),
            histogram=histogram,
            n=len(values))
        return res

