##  Module statistics.py
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
Statistics module.

The basic functions are stolen from python 3.4 stdlib

"""

from __future__ import division

import collections
import math
import operator
import functools

from fractions import Fraction
from decimal import Decimal

from .exceptions import StatisticsError
from .py3comp import xrange, iteritems


def isfinite(n):
    """Return True if x is neither an infinity nor a NaN, and False otherwise.
    (Note that 0.0 is considered finite.)

    Backported from python 3
    """

    return not (math.isinf(n) or math.isnan(n))


def sum(data, start=0):
    """sum(data [, start]) -> value

    Return a high-precision sum of the given numeric data. If optional
    argument ``start`` is given, it is added to the total. If ``data`` is
    empty, ``start`` (defaulting to 0) is returned.
    """
    n, d = exact_ratio(start)
    T = type(start)
    partials = {d: n}  # map {denominator: sum of numerators}
    # Micro-optimizations.
    coerce_types_ = coerce_types
    exact_ratio_ = exact_ratio
    partials_get = partials.get
    # Add numerators for each denominator, and track the "current" type.
    for x in data:
        T = coerce_types_(T, type(x))
        n, d = exact_ratio_(x)
        partials[d] = partials_get(d, 0) + n
    if None in partials:
        assert issubclass(T, (float, Decimal))
        assert not isfinite(partials[None])
        return T(partials[None])
    total = Fraction()
    for d, n in sorted(partials.items()):
        total += Fraction(n, d)
    if issubclass(T, int):
        assert total.denominator == 1
        return T(total.numerator)
    if issubclass(T, Decimal):
        return T(total.numerator) / total.denominator
    return T(total)


def exact_ratio(x):
    """Convert Real number x exactly to (numerator, denominator) pair.

    x is expected to be an int, Fraction, Decimal or float.
    """
    try:
        try:
            # int, Fraction
            return x.numerator, x.denominator
        except AttributeError:
            # float
            try:
                return x.as_integer_ratio()
            except AttributeError:
                # Decimal
                try:
                    return decimal_to_ratio(x)
                except AttributeError:
                    msg = "can't convert type '{}' to numerator/denominator"
                    raise TypeError(msg.format(type(x).__name__))
    except (OverflowError, ValueError):
        # INF or NAN
        return (x, None)


# FIXME This is faster than Fraction.from_decimal, but still too slow.
def decimal_to_ratio(d):
    """Convert Decimal d to exact integer ratio (numerator, denominator).
    """
    sign, digits, exp = d.as_tuple()
    if exp in ('F', 'n', 'N'):  # INF, NAN, sNAN
        assert not d.is_finite()
        raise ValueError
    num = 0
    for digit in digits:
        num = num * 10 + digit
    if sign:
        num = -num
    den = 10 ** -exp
    return (num, den)


def coerce_types(T1, T2):
    """Coerce types T1 and T2 to a common type.

    Coercion is performed according to this table, where "N/A" means
    that a TypeError exception is raised.

    +----------+-----------+-----------+-----------+----------+
    |          | int       | Fraction  | Decimal   | float    |
    +----------+-----------+-----------+-----------+----------+
    | int      | int       | Fraction  | Decimal   | float    |
    | Fraction | Fraction  | Fraction  | N/A       | float    |
    | Decimal  | Decimal   | N/A       | Decimal   | float    |
    | float    | float     | float     | float     | float    |
    +----------+-----------+-----------+-----------+----------+

    Subclasses trump their parent class; two subclasses of the same
    base class will be coerced to the second of the two.

    """
    # Get the common/fast cases out of the way first.
    if T1 is T2: return T1
    if T1 is int: return T2
    if T2 is int: return T1
    # Subclasses trump their parent class.
    if issubclass(T2, T1): return T2
    if issubclass(T1, T2): return T1
    # Floats trump everything else.
    if issubclass(T2, float): return T2
    if issubclass(T1, float): return T1
    # Subclasses of the same base class give priority to the second.
    if T1.__base__ is T2.__base__: return T2
    # Otherwise, just give up.
    raise TypeError('cannot coerce types %r and %r' % (T1, T2))


def counts(data):
    """
    Generate a table of sorted (value, frequency) pairs.
    """
    if data is None:
        raise TypeError('None is not iterable')
    table = collections.Counter(data).most_common()
    if not table:
        return table
        # Extract the values with the highest frequency.
    maxfreq = table[0][1]
    for i in range(1, len(table)):
        if table[i][1] != maxfreq:
            table = table[:i]
            break
    return table


# === Measures of central tendency (averages) ===

def mean(data):
    """Return the sample arithmetic mean of data.

    If ``data`` is empty, StatisticsError will be raised.
    """
    if iter(data) is data:
        data = list(data)
    n = len(data)
    if n < 1:
        raise StatisticsError('mean requires at least one data point')
    return sum(data) / n


# FIXME: investigate ways to calculate medians without sorting? Quickselect?
def median(data):
    """Return the median (middle value) of numeric data.

    When the number of data points is odd, return the middle data point.
    When the number of data points is even, the median is interpolated by
    taking the average of the two middle values:

    """
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("no median for empty data")
    if n % 2 == 1:
        return data[n // 2]
    else:
        i = n // 2
        return (data[i - 1] + data[i]) / 2


def median_low(data):
    """Return the low median of numeric data.

    When the number of data points is odd, the middle value is returned.
    When it is even, the smaller of the two middle values is returned.
    """
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("no median for empty data")
    if n % 2 == 1:
        return data[n // 2]
    else:
        return data[n // 2 - 1]


def median_high(data):
    """Return the high median of data.

    When the number of data points is odd, the middle value is returned.
    When it is even, the larger of the two middle values is returned.

    """
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("no median for empty data")
    return data[n // 2]


def mode(data):
    """Return the most common data point from discrete or nominal data.

    ``mode`` assumes discrete data, and returns a single value. This is the
    standard treatment of the mode as commonly taught in schools:

    If there is not exactly one most common value, ``mode`` will raise
    StatisticsError.
    """
    # Generate a table of sorted (value, frequency) pairs.
    table = counts(data)
    if len(table) == 1:
        return table[0][0]
    elif table:
        raise StatisticsError(
            'no unique mode; found %d equally common values' % len(table)
        )
    else:
        raise StatisticsError('no mode for empty data')


# === Measures of spread ===

# See http://mathworld.wolfram.com/Variance.html
#     http://mathworld.wolfram.com/SampleVariance.html
#     http://en.wikipedia.org/wiki/Algorithms_for_calculating_variance
#
# Under no circumstances use the so-called "computational formula for
# variance", as that is only suitable for hand calculations with a small
# amount of low-precision data. It has terrible numeric properties.
#
# See a comparison of three computational methods here:
# http://www.johndcook.com/blog/2008/09/26/comparing-three-methods-of-computing-standard-deviation/

def _ss(data, c=None):
    """Return sum of square deviations of sequence data.

    If ``c`` is None, the mean is calculated in one pass, and the deviations
    from the mean are calculated in a second pass. Otherwise, deviations are
    calculated from ``c`` as given. Use the second case with care, as it can
    lead to garbage results.
    """
    if c is None:
        c = mean(data)
    ss = sum((x - c) ** 2 for x in data)
    # The following sum should mathematically equal zero, but due to rounding
    # error may not.
    ss -= sum((x - c) for x in data) ** 2 / len(data)
    assert not ss < 0, 'negative sum of square deviations: %f' % ss
    return ss


def variance(data, xbar=None):
    """Return the sample variance of data.

    data should be an iterable of Real-valued numbers, with at least two
    values. The optional argument xbar, if given, should be the mean of
    the data. If it is missing or None, the mean is automatically calculated.

    Use this function when your data is a sample from a population. To
    calculate the variance from the entire population, see ``pvariance``.

    If you have already calculated the mean of your data, you can pass it as
    the optional second argument ``xbar`` to avoid recalculating it:

    This function does not check that ``xbar`` is actually the mean of
    ``data``. Giving arbitrary values for ``xbar`` may lead to invalid or
    impossible results.

    Decimals and Fractions are supported

    """
    if iter(data) is data:
        data = list(data)
    n = len(data)
    if n < 2:
        raise StatisticsError('variance requires at least two data points')
    ss = _ss(data, xbar)
    return ss / (n - 1)


def pvariance(data, mu=None):
    """Return the population variance of ``data``.

    data should be an iterable of Real-valued numbers, with at least one
    value. The optional argument mu, if given, should be the mean of
    the data. If it is missing or None, the mean is automatically calculated.

    Use this function to calculate the variance from the entire population.
    To estimate the variance from a sample, the ``variance`` function is
    usually a better choice.

    If you have already calculated the mean of the data, you can pass it as
    the optional second argument to avoid recalculating it:


    This function does not check that ``mu`` is actually the mean of ``data``.
    Giving arbitrary values for ``mu`` may lead to invalid or impossible
    results.

    Decimals and Fractions are supported:


    """
    if iter(data) is data:
        data = list(data)
    n = len(data)
    if n < 1:
        raise StatisticsError('pvariance requires at least one data point')
    ss = _ss(data, mu)
    return ss / n


def stdev(data, xbar=None):
    """Return the square root of the sample variance.

    See ``variance`` for arguments and other details.

    """
    var = variance(data, xbar)
    try:
        return var.sqrt()
    except AttributeError:
        return math.sqrt(var)


def pstdev(data, mu=None):
    """Return the square root of the population variance.

    See ``pvariance`` for arguments and other details.

    """
    var = pvariance(data, mu)
    try:
        return var.sqrt()
    except AttributeError:
        return math.sqrt(var)


def geometric_mean(data):
    """Return the geometric mean of data
    """

    if not data:
        raise StatisticsError('geometric_mean requires at least one data point')

    # in order to support negative or null values
    data = [x if x > 0 else math.e if x == 0 else 1.0 for x in data]

    return math.pow(math.fabs(functools.reduce(operator.mul, data)), 1.0 / len(data))


def harmonic_mean(data):
    """Return the harmonic mean of data
    """

    if not data:
        raise StatisticsError('harmonic_mean requires at least one data point')

    return len(data) / sum(map(lambda x: 1.0 / x if x else 0.0, data))


def skewness(data):
    """Return the skewness of the data's distribution

    """

    if not data:
        raise StatisticsError('skewness requires at least one data point')

    size = len(data)
    sd = stdev(data) ** 3

    if not sd:
        return 0.0

    mn = mean(data)
    return sum(map(lambda x: ((x - mn) ** 3 / sd), data)) / size


def kurtosis(data):
    """Return the kurtosis of the data's distribution

    """

    if not data:
        raise StatisticsError('kurtosis requires at least one data point')

    size = len(data)
    sd = stdev(data) ** 4

    if not sd:
        return 0.0

    mn = mean(data)
    return sum(map(lambda x: ((x - mn) ** 4 / sd), data)) / size - 3


def percentile(data, n):
    """Return the n-th percentile of the given data

    Assume that the data are already sorted

    """

    size = len(data)
    idx = (n / 100.0) * size - 0.5

    if idx < 0 or idx > size:
        raise StatisticsError("Too few data points ({}) for {}th percentile".format(size, n))

    return data[int(idx)]


def get_histogram(data):
    """Return the histogram relative to the given data

    Assume that the data are already sorted

    """

    count = len(data)

    if count < 2:
        raise StatisticsError('Too few data points ({}) for get_histogram'.format(count))

    min_ = data[0]
    max_ = data[-1]
    std = stdev(data)

    bins = get_histogram_bins(min_, max_, std, count)

    res = {x: 0 for x in bins}

    for value in data:
        for bin_ in bins:
            if value <= bin_:
                res[bin_] += 1
                break

    return sorted(iteritems(res))


def get_histogram_bins(min_, max_, std, count):
    """
    Return optimal bins given the input parameters

    """

    width = _get_bin_width(std, count)
    count = int(round((max_ - min_) / width) + 1)

    if count:
        bins = [i * width + min_ for i in xrange(1, count + 1)]
    else:
        bins = [min_]

    return bins


def _get_bin_width(stdev, count):
    """Return the histogram's optimal bin width based on Sturges

    http://www.jstor.org/pss/2965501
    """

    w = int(round((3.5 * stdev) / (count ** (1.0 / 3))))
    if w:
        return w
    else:
        return 1

