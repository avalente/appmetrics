AppMetrics
++++++++++

.. image:: https://travis-ci.org/avalente/appmetrics.png?branch=master
    :target: https://travis-ci.org/avalente/appmetrics
    :alt: Build status


*AppMetrics* is a python library used to collect useful run-time application's metrics, based on
`Folsom from Boundary <https://github.com/boundary/folsom>`_, which is in turn inspired by
`Metrics from Coda Hale <https://github.com/codahale/metrics>`_.

The library's purpose is to help you collect realtime metrics from your Python applications,
being them web apps, long-running batches or whatever. *AppMetrics* is not a persistent store,
you must provide your own persistence layer, maybe by using well established monitoring tools.

Usage
-----

Once that you installed *AppMetrics* package in your python environment
(a *python setup.py install* is enough), you can access it by the *metrics* module::

    >>> from appmetrics import metrics
    >>> histogram = metrics.new_histogram("test")
    >>> histogram.notify(1.0)
    True
    >>> histogram.notify(2.0)
    True
    >>> histogram.notify(3.0)
    True
    >>> histogram.get()
    {'arithmetic_mean': 2.0, 'skewness': 0.0, 'harmonic_mean': 1.6363636363636365, 'min': 1.0, 'standard_deviation': 1.0, 'median': 2.0, 'histogram': [(3.0, 3), (5.0, 0)], 'percentile': [(50, 2.0), (75, 2.0), (90, 3.0), (95, 3.0), (99, 3.0), (99.9, 3.0)], 'n': 3, 'max': 3.0, 'variance': 1.0, 'geometric_mean': 1.8171205928321397, 'kurtosis': -2.3333333333333335}

Basically you create a new metric by using one of the *metrics.new_\** functions. The metric will be stored into
an internal registry, so you can access it in different places in your application::

    >>> test_histogram = metrics.metric("test")
    >>> test_histogram.notify(4.0)
    True

The *metrics* registry is thread-safe, you can safely use it in multi-threaded web servers.


API
---

*AppMetrics* exposes a simple and consistent API: all the metric objects have three methods:
 * notify(value)   - add a new value to the metric
 * get()           - get the computed metric's value (if any)
 * raw_data()      - get the raw data stored in the metrics

However, the *notify* input type depends on the kind of metric chosen.

Metrics
-------

Several metric types are available:

Counters
********

Counter metrics provide increment and decrement capabilities for a single integer value.
The *notify* method accepts an integer: the counter will be incremented or decremented according
to the value's sign. Notice that the function tries to cast the input value to integer, so
a *TypeError* or a *ValueError* may be raised::

    >>> counter = metrics.new_counter("test")
    >>> counter.notify(10)
    >>> counter.notify(-5)
    >>> counter.get()
    5
    >>> counter.notify("wrong")
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "appmetrics/simple_metrics.py", line 40, in notify
        value = int(value)
    ValueError: invalid literal for int() with base 10: 'wrong'

Gauges
******

Gauges are point-in-time single value metrics. The *notify* method accepts any data type::

    >>> gauge = metrics.new_gauge("gauge_test")
    >>> gauge.notify("version 1.0")
    >>> gauge.get()
    'version 1.0'

The *gauge* metric is useful to expose almost-static values such as configuration parameters, constants and so on.

Histograms
**********

Histograms are collections of values on which statistical analysis are performed automatically. They are useful
to know how the application is performing. The *notify* method accepts a single floating-point value, while
the *get* method computes and returns the following values:

 * arithmetic mean
 * geometric mean
 * harmonic mean
 * data distribution histogram with automatic bins
 * kurtosis
 * maximum value
 * median
 * minimum value
 * number of values
 * 50, 75, 90, 95, 99 and 99.9th percentiles of the data distribution
 * skewness
 * standard deviation
 * variance

Notice that the *notify* method tries to cast the input value to a float, so a *TypeError* or a *ValueError* may
be raised.

Sample types
^^^^^^^^^^^^

To avoid unbound memory usage, the histogram metrics are generated from a *reservoir* of values. Currently
the only *reservoir* type available is the *uniform* one, in which a fixed number of values (default 1028)
is kept, and when the reservoir is full new values replace older ones randomly, ensuring that the
sample is always statistically representative.


Testing
-------

*AppMetrics* has an exhaustive test suite, made up by both doctests and unit tests. To run the
whole test suite (including the coverage test), just issue:

 $ nosetests --with-doctest --with-coverage --cover-package=appmetrics --cover-erase

You will need to install a couple of packages in your python environment, the list is in the "requirements.txt" file.
