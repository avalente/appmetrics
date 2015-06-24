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

from contextlib import contextmanager
import functools
import threading
import time

from .exceptions import DuplicateMetricError, InvalidMetricError
from . import histogram, simple_metrics, meter, py3comp


REGISTRY = {}
TAGS = {}
LOCK = threading.Lock()


def new_metric(name, class_, *args, **kwargs):
    """Create a new metric of the given class.

    Raise DuplicateMetricError if the given name has been already registered before

    Internal function - use "new_<type> instead"
    """

    with LOCK:
        try:
            item = REGISTRY[name]
        except KeyError:
            item = REGISTRY[name] = class_(*args, **kwargs)
            return item

    raise DuplicateMetricError("Metric {} already exists of type {}".format(name, type(item).__name__))


def delete_metric(name):
    """Remove the named metric"""

    with LOCK:
        old_metric = REGISTRY.pop(name, None)

        # look for the metric name in the tags and remove it
        for _, tags in py3comp.iteritems(TAGS):
            if name in tags:
                tags.remove(name)

    return old_metric


def metric(name):
    """
    Return the metric with the given name, if any

    Raise InvalidMetricError if the given name has not been registered
    """

    try:
        return REGISTRY[name]
    except KeyError as e:
        raise InvalidMetricError("Metric {} not found!".format(e))


def metrics():
    """
    Return the list of the returned metrics' names
    """

    return sorted(REGISTRY.keys())


def get(name):
    """
    Call "get" on the metric with the given name
    Raise InvalidMetricError if the given name has not been registered
    """

    return metric(name).get()


def notify(name, value):
    """
    Call "notify" on the metric with the given name
    Raise InvalidMetricError if the given name has not been registered
    """

    return metric(name).notify(value)


def new_histogram(name, reservoir=None):
    """
    Build a new histogram metric with a given reservoir object
    If the reservoir is not provided, a uniform reservoir with the default size is used
    """

    if reservoir is None:
        reservoir = histogram.UniformReservoir(histogram.DEFAULT_UNIFORM_RESERVOIR_SIZE)

    return new_metric(name, histogram.Histogram, reservoir)


def new_counter(name):
    """
    Build a new "counter" metric
    """

    return new_metric(name, simple_metrics.Counter)


def new_gauge(name):
    """
    Build a new "gauge" metric
    """

    return new_metric(name, simple_metrics.Gauge)


def new_meter(name, tick_interval=5):
    """
    Build a new "meter" metric
    """

    return new_metric(name, meter.Meter, tick_interval)


def new_histogram_with_implicit_reservoir(name, reservoir_type='uniform', *reservoir_args, **reservoir_kwargs):
    """
    Build a new histogram metric and a reservoir from the given parameters
    """

    reservoir = new_reservoir(reservoir_type, *reservoir_args, **reservoir_kwargs)
    return new_histogram(name, reservoir)


def new_reservoir(reservoir_type='uniform', *reservoir_args, **reservoir_kwargs):
    """
    Build a new reservoir
    """

    try:
        reservoir_cls = RESERVOIR_TYPES[reservoir_type]
    except KeyError:
        raise InvalidMetricError("Unknown reservoir type: {}".format(reservoir_type))

    return reservoir_cls(*reservoir_args, **reservoir_kwargs)


def get_or_create_histogram(name, reservoir_type, *reservoir_args, **reservoir_kwargs):
    """
    Will return a histogram matching the given parameters or raise
    DuplicateMetricError if it can't be created due to a name collision
    with another histogram with different parameters.
    """
    reservoir = new_reservoir(reservoir_type, *reservoir_args, **reservoir_kwargs)

    try:
        hmetric = new_histogram(name, reservoir)
    except DuplicateMetricError:
        hmetric = metric(name)
        if not isinstance(hmetric, histogram.Histogram):
            raise DuplicateMetricError(
                "Metric {!r} already exists of type {!r}".format(name, type(hmetric).__name__))

        if not hmetric.reservoir.same_kind(reservoir):
            raise DuplicateMetricError(
                "Metric {!r} already exists with a different reservoir: {}".format(name, hmetric.reservoir))

    return hmetric


def with_histogram(name, reservoir_type="uniform", *reservoir_args, **reservoir_kwargs):
    """
    Time-measuring decorator: the time spent in the wrapped function is measured
    and added to the named metric.
    metric_args and metric_kwargs are passed to new_histogram()
    """

    hmetric = get_or_create_histogram(name, reservoir_type, *reservoir_args, **reservoir_kwargs)

    def wrapper(f):

        @functools.wraps(f)
        def fun(*args, **kwargs):
            t1 = time.time()
            res = f(*args, **kwargs)
            t2 = time.time()

            hmetric.notify(t2-t1)
            return res

        return fun

    return wrapper


def with_meter(name, tick_interval=meter.DEFAULT_TICK_INTERVAL):
    """
    Call-counting decorator: each time the wrapped function is called
    the named meter is incremented by one.
    metric_args and metric_kwargs are passed to new_meter()
    """

    try:
        mmetric = new_meter(name, tick_interval)
    except DuplicateMetricError as e:
        mmetric = metric(name)

        if not isinstance(mmetric, meter.Meter):
            raise DuplicateMetricError("Metric {!r} already exists of type {}".format(name, type(mmetric).__name__))

        if tick_interval != mmetric.tick_interval:
            raise DuplicateMetricError("Metric {!r} already exists: {}".format(name, mmetric))

    def wrapper(f):

        @functools.wraps(f)
        def fun(*args, **kwargs):
            res = f(*args, **kwargs)

            mmetric.notify(1)
            return res

        return fun

    return wrapper


@contextmanager
def timer(name, reservoir_type="uniform", *reservoir_args, **reservoir_kwargs):
    """
    Time-measuring context manager: the time spent in the wrapped block
    if measured and added to the named metric.
    """

    hmetric = get_or_create_histogram(name, reservoir_type, *reservoir_args, **reservoir_kwargs)

    t1 = time.time()
    yield
    t2 = time.time()
    hmetric.notify(t2 - t1)


def tag(name, tag_name):
    """
    Tag the named metric with the given tag.
    """

    with LOCK:
        # just to check if <name> exists
        metric(name)

        TAGS.setdefault(tag_name, set()).add(name)


def tags():
    """
    Return the currently defined tags.
    """

    # protect global value against accidental modifications
    return TAGS.copy()


def metrics_by_tag(tag_name):
    """
    Return a dictionary with {metric name: metric values} for all the metrics with the given tag.
    Return an empty dictionary if the given tag does not exist.
    """

    try:
        names = TAGS[tag_name]
    except KeyError:
        return {}

    return metrics_by_name_list(names)


def untag(name, tag_name):
    """
    Remove the given tag from the given metric.
    Return True if the metric was tagged, False otherwise
    """

    with LOCK:
        by_tag = TAGS.get(tag_name, None)
        if not by_tag:
            return False
        try:
            by_tag.remove(name)

            # remove the tag if no associations left
            if not by_tag:
                TAGS.pop(tag_name)

            return True
        except KeyError:
            return False


def metrics_by_name_list(names):
    """
    Return a dictionary with {metric name: metric value} for all the metrics with the given names.
    """
    results = {}

    for name in names:
        # no lock - a metric could have been removed in the meanwhile
        try:
            results[name] = get(name)
        except InvalidMetricError:
            continue

    return results


RESERVOIR_TYPES = {
    'uniform': histogram.UniformReservoir,
    'sliding_window': histogram.SlidingWindowReservoir,
    'sliding_time_window': histogram.SlidingTimeWindowReservoir,
    'exp_decaying': histogram.ExponentialDecayingReservoir,
}


METRIC_TYPES = {
    'histogram': new_histogram_with_implicit_reservoir,
    'gauge': new_gauge,
    'counter': new_counter,
    'meter': new_meter,
}