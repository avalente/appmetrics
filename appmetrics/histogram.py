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

import random
import threading

from . import statistics, exceptions


DEFAULT_UNIFORM_RESERVOIR_SIZE = 1028


class UniformReservoir(object):
    """
    A random sampling reservoir of floating-point values. Uses Vitter's Algorithm R to produce a statistically
    representative sample (http://www.cs.umd.edu/~samir/498/vitter.pdf)
    """

    def __init__(self, size=DEFAULT_UNIFORM_RESERVOIR_SIZE):
        self.size = size
        self._values = [0] * size
        self.count = 0
        self.lock = threading.Lock()

    def add(self, value):
        """
        Add a value to the reservoir
        The value will be casted to a floating-point, so a TypeError or a ValueError may be raised.
        """

        if not isinstance(value, float):
            value = float(value)

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

    @property
    def values(self):
        """
        Return the stored values
        """

        if self.count < self.size:
            return self._values[:self.count]
        return self._values

    @property
    def sorted_values(self):
        """
        Sort and return the current sample values
        """
        return sorted(self.values)


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

