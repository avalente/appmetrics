##  Module metrics.py
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
Main interface module
"""

import threading

from .exceptions import DuplicateMetricError, InvalidMetricError
from . import histogram

REGISTRY = {}
LOCK = threading.Lock()


def new_metric(name, class_, *args, **kwargs):
    """Create a new metric of the given class.

    Raises DuplicateMetricError if the given name has been already registered before

    Internal function - use "new_<type> instead"
    """

    with LOCK:
        try:
            item = REGISTRY[name]
        except KeyError:
            item = REGISTRY[name] = class_(*args, **kwargs)
            return item

    raise DuplicateMetricError("Metric {} already exists of type {}".format(name, type(item).__name__))


def metric(name):
    """
    Return the metric with the given name, if any

    Raises InvalidMetricError if the given name has not been registered
    """

    try:
        return REGISTRY[name]
    except KeyError, e:
        raise InvalidMetricError("Metric {} not found!".format(e))


def new_histogram(name, size=histogram.DEFAULT_UNIFORM_RESERVOIR_SIZE):
    """
    Build a new histogram metric with a uniform reservoir of configurable size
    """
    reservoir = histogram.UniformReservoir(size)
    return new_metric(name, histogram.Histogram, reservoir)
