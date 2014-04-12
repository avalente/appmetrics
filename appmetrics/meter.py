##  Module meter.py
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
Meter metric - measures throughput at various time intervals
"""

import math
import time
import threading


DEFAULT_TICK_INTERVAL = 5


class EWMA(object):
    """
    Compute exponential-weighted moving average of values incoming at a fixed rate.

    http://en.wikipedia.org/wiki/Moving_average#Exponential_moving_average
    """

    def __init__(self, time_period, tick_interval):
        """
        time_unit is the period of time on which the moving average is computed,
        expressed in minutes
        """

        self.time_period = time_period
        self.tick_interval = tick_interval

        self.rate = 0.0
        self.value = 0
        self.initialized = False

        self.alpha = self.compute_alpha(time_period, tick_interval)

        self.lock = threading.Lock()

    @staticmethod
    def compute_alpha(period, interval):
        """Compute exponential smoothing factor"""

        return 1 - math.exp(-interval / (60.0 * period))

    def update(self, value):
        """
        Update the current rate with the given value.
        The value must be an integer.
        """

        value = int(value)

        with self.lock:
            self.value += value

    def tick(self):
        """Decay the current rate according to the elapsed time"""

        instant_rate = float(self.value) / float(self.tick_interval)

        with self.lock:
            if self.initialized:
                self.rate += (self.alpha * (instant_rate - self.rate))
            else:
                self.initialized = True
                self.rate = instant_rate

            self.value = 0


class Meter(object):
    """
    A meter metric which measures mean throughput and one, five, and fifteen-minute
    exponentially-weighted moving average throughputs.
    This is very similar to the unix "load average" metric. All the throughput
    values are expressed in number of operation per second.
    """

    def __init__(self, tick_interval=DEFAULT_TICK_INTERVAL):
        self.tick_interval = tick_interval

        # one minute
        self.m1 = EWMA(1, tick_interval)
        # five minutes
        self.m5 = EWMA(5, tick_interval)
        # fifteen minutes
        self.m15 = EWMA(15, tick_interval)
        # one day
        self.day = EWMA(60 * 24, tick_interval)

        self.started_on = self.latest_tick = time.time()

        self.count = 0

        self.lock = threading.Lock()

    def notify(self, value):
        """Add a new observation to the metric"""

        with self.lock:
            #TODO: this could slow down slow-rate incoming updates
            # since the number of ticks depends on the actual time
            # passed since the latest notification. Consider using
            # a real timer to tick the EWMA.

            self.tick()

            for avg in (self.m1, self.m5, self.m15, self.day):
                avg.update(value)
            self.count += value

    def tick_all(self, times):
        """
        Tick all the EWMAs for the given number of times
        """

        for i in range(times):
            for avg in (self.m1, self.m5, self.m15, self.day):
                avg.tick()

    def tick(self):
        """
        Emulate a timer: in order to avoid a real timer we "tick" a number
        of times depending on the actual time passed since the last tick
        """

        now = time.time()

        elapsed = now - self.latest_tick

        if elapsed > self.tick_interval:
            ticks = int(elapsed / self.tick_interval)

            self.tick_all(ticks)

            self.latest_tick = now

    def raw_data(self):
        """Return the raw underlying data"""

        return self.count

    def get(self):
        """
        Return the computed statistics over the gathered data
        """

        with self.lock:
            self.tick()

            data = dict(
                kind="meter",
                count=self.count,
                mean=self.count / (time.time() - self.started_on),
                one=self.m1.rate,
                five=self.m5.rate,
                fifteen=self.m15.rate,
                day=self.day.rate)

        return data

    def __repr__(self):
        return "{}({})".format(type(self).__name__, self.tick_interval)
