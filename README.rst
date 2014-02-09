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

Testing
-------

*AppMetrics* has an exhaustive test suite, made up by both doctests and unit tests. To run the
whole test suite (including the coverage test), just issue:

 $ nosetests --with-doctest --with-coverage --cover-package=appmetrics --cover-erase

You will need to install a couple of packages in your python environment, the list is in the "requirements.txt" file.
