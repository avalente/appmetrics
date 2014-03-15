AppMetrics
++++++++++

.. image:: https://travis-ci.org/avalente/appmetrics.png?branch=master
    :target: https://travis-ci.org/avalente/appmetrics
    :alt: Build status


.. image:: https://coveralls.io/repos/avalente/appmetrics/badge.png
    :target: https://coveralls.io/r/avalente/appmetrics
    :alt: Code coverage


``AppMetrics`` is a python library used to collect useful run-time application's metrics, based on
`Folsom from Boundary <https://github.com/boundary/folsom>`_, which is in turn inspired by
`Metrics from Coda Hale <https://github.com/codahale/metrics>`_.

The library's purpose is to help you collect real-time metrics from your Python applications,
being them web apps, long-running batches or whatever. ``AppMetrics`` is not a persistent store,
you must provide your own persistence layer, maybe by using well established monitoring tools.

Usage
-----

Once you have installed ``AppMetrics`` package in your python environment
(a ``pip install appmetrics`` is usually enough), you can access it by the ``metrics`` module::

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

Basically you create a new metric by using one of the ``metrics.new_*`` functions. The metric will be stored into
an internal registry, so you can access it in different places in your application::

    >>> test_histogram = metrics.metric("test")
    >>> test_histogram.notify(4.0)
    True

The ``metrics`` registry is thread-safe, you can safely use it in multi-threaded web servers.


Decorators
**********

The ``metrics`` module also provides a couple of decorators: ``with_histogram`` and ``with_meter`` which are
an easy and fast way to use ``AppMetrics``: just decorate your functions/methods and you will have metrics
collected for them. You can decorate multiple functions with the same metric's name, as long as the decorator's
type is the same, or a ``DuplicateMetricError`` will be raised. If you decorate two functions with the same
type and name but different parameters, the second one's parameters will be ignored: the first metric
definition will be used and a warning will be issued.
See the documentation for `Histograms`_ and `Meters`_ for more details.


API
---

``AppMetrics`` exposes a simple and consistent API; all the metric objects have three methods:

 * ``notify(value)``   - add a new value to the metric
 * ``get()``           - get the computed metric's value (if any)
 * ``raw_data()``      - get the raw data stored in the metrics

However, the ``notify`` input type depends on the kind of metric chosen.

Metrics
-------

Several metric types are available:

Counters
********

Counter metrics provide increment and decrement capabilities for a single integer value.
The ``notify`` method accepts an integer: the counter will be incremented or decremented according
to the value's sign. Notice that the function tries to cast the input value to integer, so
a ``TypeError`` or a ``ValueError`` may be raised::

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

Gauges are point-in-time single value metrics. The ``notify`` method accepts any data type::

    >>> gauge = metrics.new_gauge("gauge_test")
    >>> gauge.notify("version 1.0")
    >>> gauge.get()
    'version 1.0'

The ``gauge`` metric is useful to expose almost-static values such as configuration parameters, constants and so on.
Although you can use any python data type as the value, you won't be able to use the ``wsgi`` middleware unless
you use a valid ``json`` type.

Histograms
**********

Histograms are collections of values on which statistical analysis are performed automatically. They are useful
to know how the application is performing. The ``notify`` method accepts a single floating-point value, while
the ``get`` method computes and returns the following values:

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

Notice that the ``notify`` method tries to cast the input value to a float, so a ``TypeError`` or a ``ValueError`` may
be raised.

You can use the histogram metric also by the ``with_histogram`` decorator: the time spent in the decorated
function will be collected by an ``histogram`` with the given name::

    >>> @metrics.with_histogram("histogram_test")
    ... def fun(v):
    ...     return v*2
    ...
    >>> fun(10)
    20
    >>> metrics.metric("histogram_test").raw_data()
    [5.9604644775390625e-06]

Sample types
^^^^^^^^^^^^

To avoid unbound memory usage, the histogram metrics are generated from a *reservoir* of values. Currently
the only *reservoir* type available is the *uniform* one, in which a fixed number of values (default 1028)
is kept, and when the reservoir is full new values replace older ones randomly, ensuring that the
sample is always statistically representative.

Meters
******

Meters are increment-only counters that measure the rate of events (such as ``"http requests"``) over time. This kind of
metric is useful to collect throughput values (such as ``"requests per second"``), both on average and on different time
intervals::

    >>> meter = metrics.new_meter("meter_test")
    >>> meter.notify(1)
    >>> meter.notify(1)
    >>> meter.notify(3)
    >>> meter.get()
    {'count': 5, 'five': 0.01652854617838251, 'mean': 0.34341050858242983, 'fifteen': 0.005540151995103271, 'day': 5.7868695912732804e-05, 'one': 0.07995558537067671}

The return values of the ``get`` method are the following:

 * ``count``: number of operations collected so far
 * ``mean``: the average throughput since the metric creation
 * ``one``: one-minute
   `exponentially-weighted moving average <http://en.wikipedia.org/wiki/Moving_average#Exponential_moving_average>`_
   (*EWMA*)
 * ``five``: five-minutes *EWMA*
 * ``fifteen``: fifteen-minutes *EWMA*
 * ``day``: last day *EWMA*

Notice that the ``notify`` method tries to cast the input value to an integer, so a ``TypeError`` or a ``ValueError``
may be raised.

You can use the meter metric also by the ``with_meter`` decorator: the number of calls to the decorated
function will be collected by a ``meter`` with the given name.

External access
---------------

You can access the metrics provided by ``AppMetrics`` externally by the ``WSGI``
middleware found in ``appmetrics.wsgi.AppMetricsMiddleware``. It is a standard ``WSGI``
middleware without external dependencies and it can be plugged in any framework supporting
the ``WSGI`` standard, for example in a ``Flask`` application::

    from flask import Flask
    from appmetrics import metrics

    metrics.new_histogram("test-histogram")
    metrics.new_gauge("test-counter")
    metrics.metric("test-counter").notify(10)

    app = Flask(__name__)

    @app.route('/hello')
    def hello_world():
        return 'Hello World!'

    if __name__ == '__main__':
        from appmetrics.wsgi import AppMetricsMiddleware
        app.wsgi_app = AppMetricsMiddleware(app.wsgi_app)
        app.run()

If you launch the above application you can ask for metrics::

    $ curl http://localhost:5000/hello
    Hello World!

    $ curl http://localhost:5000/_app-metrics
    ["test-counter", "test-histogram"]

    $ curl http://localhost:5000/_app-metrics/test-counter
    10

In this way you can easily expose your application's metrics to an external monitoring service.
Moreover, since the ``AppMetricsMiddleware`` exposes a full *RESTful API*, you can create metrics
from anywhere and also populate them with foreign application's data.

Usage
*****

As usual, instantiate the middleware with the wrapped ``WSGI`` application; it looks for
request paths starting with ``"/_app-metrics"``: if not found, the wrapped application
is called. The following resources are defined:

``/_app-metrics``
  - **GET**: return the list of the registered metrics
``/_app-metrics/<name>``
  - **GET**: return the value of the given metric or ``404``.
  - **PUT**: create a new metric with the given name. The body must be a ``JSON`` object with a
    mandatory attribute named ``"type"`` which must be one of the metrics types allowed,
    by the ``"metrics.METRIC_TYPES"`` dictionary, while the other attributes are
    passed to the ``new_<type>`` function as keyword arguments.
    Request's ``content-type`` must be ``"application/json"``.
  - **POST**: add a new value to the metric. The body must be a ``JSON`` object with a mandatory
    attribute named ``"value"``: the notify method will be called with the given value.
    Other attributes are ignored.
    Request's ``content-type`` must be ``"application/json"``.


The root doesn't have to be ``"/_app-metrics"``, you can customize it by providing your own to
the middleware constructor.

A standalone ``AppMetrics`` webapp can be started by using ``werkzeug``'s development server::

    $ python -m werkzeug.serving appmetrics.wsgi.standalone_app
    * Running on http://127.0.0.1:5000/

The standalone app mounts on the root (no ``_app-metrics`` prefix). DON'T use it for production purposes!!!


Testing
-------

``AppMetrics`` has an exhaustive, fully covering test suite, made up by both doctests and unit tests. To run the
whole test suite (including the coverage test), just issue::

    $ nosetests --with-doctest --with-coverage --cover-package=appmetrics --cover-erase

You will need to install a couple of packages in your python environment, the list is in the
``"requirements.txt"`` file.
