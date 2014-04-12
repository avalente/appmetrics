##  Module simple_metrics.py
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
Implementation of simple metrics
"""

import threading


class Counter(object):
    """
    Counter metrics provide increment and decrement capabilities for a single integer value.
    """

    def __init__(self):
        self.value = 0

        self.lock = threading.Lock()

    def notify(self, value):
        """
        Increment or decrement the value, according to the given value's sign

        The value should be an integer, an attempt to cast it to integer will be made
        """
        value = int(value)

        with self.lock:
            self.value += value

    def get(self):
        """
        Return the counter's value
        """
        return dict(kind="counter", value=self.value)

    def raw_data(self):
        """
        Return the raw value
        """
        return self.value


class Gauge(object):
    """
    Gauges are point-in-time single value metrics.
    """

    def __init__(self):
        self.value = None

        self.lock = threading.Lock()

    def notify(self, value):
        """
        Set the current value for the gauge. The value may be any python value
        """

        with self.lock:
            self.value = value

    def get(self):
        """
        Return the gauge's current value
        """

        return dict(kind="gauge", value=self.value)

    def raw_data(self):
        return self.value
