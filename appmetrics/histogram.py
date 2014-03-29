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

from . import statistics, exceptions


DEFAULT_UNIFORM_RESERVOIR_SIZE = 1028


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
                k = random.randint(0, self.count - 1)
                if k < self.size:
                    self._values[k] = value
                    changed = True

        self.count += 1

        return changed

    def _get_values(self):
        if self.count < self.size:
            return self._values[:self.count]
        return self._values

    def _same_parameters(self, other):
        return self.size == other.size

    def __repr__(self):
        return "{}({})".format(type(self).__name__, self.size)


class SlidingWindowReservoir(ReservoirBase):
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
            percentile=zip(plevels, percentiles),
            histogram=histogram,
            n=len(values))
        return res

