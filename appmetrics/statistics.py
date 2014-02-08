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

from fractions import Fraction
from decimal import Decimal

from .exceptions import StatisticsError


def isfinite(n):
    """Return True if x is neither an infinity nor a NaN, and False otherwise.
    (Note that 0.0 is considered finite.)

    Backported from python 3

    >>> isfinite(0.0)
    True

    >>> isfinite(1.0)
    True

    >>> isfinite(5)
    True

    >>> isfinite(float("nan"))
    False

    >>> isfinite(float("inf"))
    False

    """

    return not (math.isinf(n) or math.isnan(n))


def sum(data, start=0):
    """sum(data [, start]) -> value

    Return a high-precision sum of the given numeric data. If optional
    argument ``start`` is given, it is added to the total. If ``data`` is
    empty, ``start`` (defaulting to 0) is returned.


    Examples
    --------

    >>> sum([3, 2.25, 4.5, -0.5, 1.0], 0.75)
    11.0

    Some sources of round-off error will be avoided:

    >>> sum([1e50, 1, -1e50] * 1000)  # Built-in sum returns zero.
    1000.0

    Fractions and Decimals are also supported:

    >>> from fractions import Fraction as F
    >>> sum([F(2, 3), F(7, 5), F(1, 4), F(5, 6)])
    Fraction(63, 20)

    >>> from decimal import Decimal as D
    >>> data = [D("0.1375"), D("0.2108"), D("0.3061"), D("0.0419")]
    >>> sum(data)
    Decimal('0.6963')

    >>> sum([1, float("nan")])
    nan

    """
    n, d = _exact_ratio(start)
    T = type(start)
    partials = {d: n}  # map {denominator: sum of numerators}
    # Micro-optimizations.
    coerce_types = _coerce_types
    exact_ratio = _exact_ratio
    partials_get = partials.get
    # Add numerators for each denominator, and track the "current" type.
    for x in data:
        T = _coerce_types(T, type(x))
        n, d = exact_ratio(x)
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


def _exact_ratio(x):
    """Convert Real number x exactly to (numerator, denominator) pair.

    >>> _exact_ratio(0.25)
    (1, 4)

    >>> _exact_ratio(None)
    Traceback (most recent call last):
        ...
    TypeError: can't convert type 'NoneType' to numerator/denominator

    >>> _exact_ratio(float("nan"))
    (nan, None)

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
                    return _decimal_to_ratio(x)
                except AttributeError:
                    msg = "can't convert type '{}' to numerator/denominator"
                    raise TypeError(msg.format(type(x).__name__))
    except (OverflowError, ValueError):
        # INF or NAN
        return (x, None)


# FIXME This is faster than Fraction.from_decimal, but still too slow.
def _decimal_to_ratio(d):
    """Convert Decimal d to exact integer ratio (numerator, denominator).

    >>> from decimal import Decimal
    >>> _decimal_to_ratio(Decimal("2.6"))
    (26, 10)

    >>> _decimal_to_ratio(Decimal("nan"))
    Traceback (most recent call last):
        ...
    ValueError

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


def _coerce_types(T1, T2):
    """Coerce types T1 and T2 to a common type.

    >>> _coerce_types(int, float)
    <type 'float'>

    >>> class I1(int): pass
    >>> class I2(I1): pass
    >>> class I3(I1): pass
    >>> class I4(I2): pass

    >>> _coerce_types(I1, I2)
    <class 'appmetrics.statistics.I2'>

    >>> _coerce_types(I2, I1)
    <class 'appmetrics.statistics.I2'>

    >>> _coerce_types(I1, float)
    <type 'float'>

    >>> _coerce_types(float, I1)
    <type 'float'>

    >>> _coerce_types(I2, I3)
    <class 'appmetrics.statistics.I3'>

    >>> _coerce_types(I4, I3)
    Traceback (most recent call last):
        ...
    TypeError: cannot coerce types <class 'appmetrics.statistics.I4'> and <class 'appmetrics.statistics.I3'>

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


def _counts(data):
    """
    Generate a table of sorted (value, frequency) pairs.

    >>> _counts(None)
    Traceback (most recent call last):
        ...
    TypeError: None is not iterable

    >>> _counts([])
    []

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

    >>> mean([1, 2, 3, 4, 4])
    2.8

    >>> from fractions import Fraction as F
    >>> mean([F(3, 7), F(1, 21), F(5, 3), F(1, 3)])
    Fraction(13, 21)

    >>> from decimal import Decimal as D
    >>> mean([D("0.5"), D("0.75"), D("0.625"), D("0.375")])
    Decimal('0.5625')

    >>> mean(iter([1, 2, 3]))
    2.0

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

    >>> median([1, 3, 5])
    3
    >>> median([1, 3, 5, 7])
    4.0

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

    >>> median_low([1, 3, 5])
    3
    >>> median_low([1, 3, 5, 7])
    3

    >>> median_low([])
    Traceback (most recent call last):
        ...
    StatisticsError: no median for empty data


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

    >>> median_high([1, 3, 5])
    3
    >>> median_high([1, 3, 5, 7])
    5

    >>> median_high([])
    Traceback (most recent call last):
        ...
    StatisticsError: no median for empty data

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

    >>> mode([1, 1, 2, 3, 3, 3, 3, 4])
    3

    This also works with nominal (non-numeric) data:

    >>> mode(["red", "blue", "blue", "red", "green", "red", "red"])
    'red'

    >>> mode(["red", "blue", "blue", "red"])
    Traceback (most recent call last):
        ...
    StatisticsError: no unique mode; found 2 equally common values

    >>> mode([])
    Traceback (most recent call last):
        ...
    StatisticsError: no mode for empty data

    If there is not exactly one most common value, ``mode`` will raise
    StatisticsError.
    """
    # Generate a table of sorted (value, frequency) pairs.
    table = _counts(data)
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

    Examples:

    >>> data = [2.75, 1.75, 1.25, 0.25, 0.5, 1.25, 3.5]
    >>> variance(data)
    1.3720238095238095

    If you have already calculated the mean of your data, you can pass it as
    the optional second argument ``xbar`` to avoid recalculating it:

    >>> m = mean(data)
    >>> variance(data, m)
    1.3720238095238095

    This function does not check that ``xbar`` is actually the mean of
    ``data``. Giving arbitrary values for ``xbar`` may lead to invalid or
    impossible results.

    Decimals and Fractions are supported:

    >>> from decimal import Decimal as D
    >>> variance([D("27.5"), D("30.25"), D("30.25"), D("34.5"), D("41.75")])
    Decimal('31.01875')

    >>> from fractions import Fraction as F
    >>> variance([F(1, 6), F(1, 2), F(5, 3)])
    Fraction(67, 108)

    >>> variance(iter([1, 2, 5]))
    4.333333333333334

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

    Examples:

    >>> data = [0.0, 0.25, 0.25, 1.25, 1.5, 1.75, 2.75, 3.25]
    >>> pvariance(data)
    1.25

    If you have already calculated the mean of the data, you can pass it as
    the optional second argument to avoid recalculating it:

    >>> mu = mean(data)
    >>> pvariance(data, mu)
    1.25

    This function does not check that ``mu`` is actually the mean of ``data``.
    Giving arbitrary values for ``mu`` may lead to invalid or impossible
    results.

    Decimals and Fractions are supported:

    >>> from decimal import Decimal as D
    >>> pvariance([D("27.5"), D("30.25"), D("30.25"), D("34.5"), D("41.75")])
    Decimal('24.815')

    >>> from fractions import Fraction as F
    >>> pvariance([F(1, 4), F(5, 4), F(1, 2)])
    Fraction(13, 72)

    >>> pvariance(iter([1, 2, 3]))
    0.6666666666666666

    >>> pvariance([])
    Traceback (most recent call last):
        ...
    StatisticsError: pvariance requires at least one data point


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

    >>> stdev([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])
    1.0810874155219827

    """
    var = variance(data, xbar)
    try:
        return var.sqrt()
    except AttributeError:
        return math.sqrt(var)


def pstdev(data, mu=None):
    """Return the square root of the population variance.

    See ``pvariance`` for arguments and other details.

    >>> pstdev([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])
    0.986893273527251

    """
    var = pvariance(data, mu)
    try:
        return var.sqrt()
    except AttributeError:
        return math.sqrt(var)


def geometric_mean(data):
    """Return the geometric mean of data

    >>> geometric_mean([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])
    2.7121486566834387

    >>> geometric_mean([1.5, 2.5, 2.5, 2.75, -3.25, 4.75])
    2.2284330795786698

    >>> geometric_mean([1.5, 2.5, 2.5, 2.75, 0, 4.75])
    2.63258262293452

    >>> geometric_mean([])
    Traceback (most recent call last):
        ...
    StatisticsError: geometric_mean requires at least one data point

    """

    if not data:
        raise StatisticsError('geometric_mean requires at least one data point')

    # in order to support negative or null values
    data = [x if x > 0 else math.e if x == 0 else 1.0 for x in data]

    return math.pow(math.fabs(reduce(operator.mul, data)), 1.0 / len(data))


def harmonic_mean(data):
    """Return the harmonic mean of data

    >>> harmonic_mean([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])
    2.5547986710408086

    >>> harmonic_mean([1.5, 2.5, 2.5, 2.75, -3.25, 4.75])
    3.4619305150494095

    >>> harmonic_mean([1.5, 2.5, 2.5, 2.75, 0, 4.75])
    2.9399812441387936

    >>> harmonic_mean([])
    Traceback (most recent call last):
        ...
    StatisticsError: harmonic_mean requires at least one data point

    """

    if not data:
        raise StatisticsError('harmonic_mean requires at least one data point')

    return len(data) / sum(map(lambda x: 1.0 / x if x else 0.0, data))


def skewness(data):
    """Return the skewness of the data's distribution

    >>> skewness([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])
    0.5193819834930741

    >>> skewness([1.5, 2.5, 2.5, 2.75, -3.25, 4.75])
    -0.8623011014727693

    >>> skewness([1.5, 2.5, 2.5, 2.75, 0, 4.75])
    0.03989169123327498

    >>> skewness([])
    Traceback (most recent call last):
        ...
    StatisticsError: skewness requires at least one data point

    """

    if not data:
        raise StatisticsError('skewness requires at least one data point')

    size = len(data)
    sd = stdev(data) ** 3
    mn = mean(data)
    return sum(map(lambda x: ((x - mn) ** 3 / sd), data)) / size


def kurtosis(data):
    """Return the kurtosis of the data's distribution

    >>> kurtosis([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])
    -1.0485692089183762

    >>> kurtosis([1.5, 2.5, 2.5, 2.75, -3.25, 4.75])
    -0.6949222688831207

    >>> kurtosis([1.5, 2.5, 2.5, 2.75, 0, 4.75])
    -1.2034104454720884

    >>> kurtosis([])
    Traceback (most recent call last):
        ...
    StatisticsError: kurtosis requires at least one data point

    """

    if not data:
        raise StatisticsError('kurtosis requires at least one data point')

    size = len(data)
    sd = stdev(data) ** 4
    mn = mean(data)
    return sum(map(lambda x: ((x - mn) ** 4 / sd), data)) / size - 3


def percentile(data, n):
    """Return the n-th percentile of the given data

    Assume that the data are already sorted

    >>> percentile([1.5, 2.5, 2.5, 2.75, 3.25, 4.75], 50)
    2.5

    >>> percentile([1.5, 2.5, 2.5, 2.75, 3.25, 4.75], 99)
    4.75

    >>> percentile([1.5, 2.5, 2.5, 2.75, 3.25, 4.75], 10)
    1.5

    >>> percentile([1.5, 2.5, 2.5, 2.75, 3.25, 4.75], 1)
    Traceback (most recent call last):
        ...
    StatisticsError: Too few data points (6) for 1th percentile

    >>> percentile([], 90)
    Traceback (most recent call last):
        ...
    StatisticsError: Too few data points (0) for 90th percentile

    """

    size = len(data)
    idx = (n / 100.0) * size - 0.5

    if idx < 0 or idx > size:
        raise StatisticsError("Too few data points ({}) for {}th percentile".format(size, n))

    return data[int(idx)]


def get_histogram(data):
    """Return the histogram relative to the given data

    Assume that the data are already sorted

    >>> get_histogram([1.5, 2.5, 2.5, 2.75, 3.25, 4.75, 5.0])
    [(3.5, 5), (5.5, 2), (7.5, 0)]

    >>> get_histogram([1.0, 1.0, 1.0])
    [(2.0, 3)]

    >>> get_histogram([1.5])
    Traceback (most recent call last):
        ...
    StatisticsError: Too few data points (1) for get_histogram

    """

    count = len(data)

    if count < 2:
        raise StatisticsError('Too few data points ({}) for get_histogram'.format(count))

    min_ = data[0]
    max_ = data[-1]
    std = stdev(data)

    bins = _get_histogram_bins(min_, max_, std, count)

    res = {x: 0 for x in bins}

    for value in data:
        for bin_ in bins:
            if value <= bin_:
                res[bin_] += 1
                break

    return sorted(res.iteritems())


def _get_histogram_bins(min_, max_, std, count):
    """
    Return optimal bins given the input parameters

    >>> _get_histogram_bins(1, 3, 0.5, 5)
    [2, 3, 4]

    >>> _get_histogram_bins(1, 2, -1/3.5, 1.0)
    [1]

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

