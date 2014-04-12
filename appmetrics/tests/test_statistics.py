import math
from fractions import Fraction as F
from decimal import Decimal as D

from nose import tools as nt

from .. import statistics as mm
from ..exceptions import StatisticsError

"""adapted from original doctests"""

def test_isfinite():
    cases = [(0.0, True),
             (1.0, True),
             (5, True),
             (float("nan"), False),
             (float("inf"), False)]

    for v, expected in cases:
        check = lambda x: nt.assert_equal(mm.isfinite(x), expected)
        yield check, v

def test_coerce_types():
    class I1(int): pass
    class I2(I1): pass
    class I3(I1): pass
    class I4(I2): pass

    cases = [(int, float, float),
                (I1, I2, I2),
                (I2, I1, I2),
                (I1, float, float),
                (float, I1, float),
                (I2, I3, I3),
                (I4, I3, TypeError)]

    def check(x, y, expected):
        if issubclass(expected, Exception):
            nt.assert_raises(expected, mm.coerce_types, x, y)
        else:
            nt.assert_is(mm.coerce_types(x, y), expected)

    for x, y, res in cases:
        yield check, x, y, res

def test_sum_plain():
    value = mm.sum([3, 2.25, 4.5, -0.5, 1.0], 0.75)
    nt.assert_equal(value, 11.0)

def test_sum_extreme():
    value = mm.sum([1e50, 1, -1e50] * 1000)  # Built-in sum returns zero.
    nt.assert_equal(value, 1000.0)

def test_sum_with_fractions():
    value = mm.sum([F(2, 3), F(7, 5), F(1, 4), F(5, 6)])
    nt.assert_equal(value, F(63, 20))

def test_sum_with_decimals():
    data = [D("0.1375"), D("0.2108"), D("0.3061"), D("0.0419")]
    nt.assert_equal(mm.sum(data), D('0.6963'))

def test_sum_with_nan():
    nt.assert_true(math.isnan(mm.sum([1, float("nan")])))

def test_exact_ratio():
    nt.assert_equal(mm.exact_ratio(0.25), (1, 4))

@nt.raises(TypeError)
def test_exact_ratio_None():
    mm.exact_ratio(None)

def test_exact_ratio_nan():
    n, d = mm.exact_ratio(float("nan"))
    nt.assert_true(math.isnan(n))
    nt.assert_is_none(d)

def test_decimal_to_ratio():
    nt.assert_equal(mm.decimal_to_ratio(D("2.6")), (26, 10))

@nt.raises(ValueError)
def test_decimal_to_ratio_nan():
    mm.decimal_to_ratio(D("nan"))

@nt.raises(TypeError)
def test_counts_not_iterable():
    mm.counts(None)

def test_counts():
    nt.assert_equal(mm.counts([1, 2, 2, 3, 2, 4, 2]), [(2, 4)])

def test_mean():
    nt.assert_equal(mm.mean([1, 2, 3, 4, 4]), 2.8)

def test_mean_fractions():
    value = mm.mean([F(3, 7), F(1, 21), F(5, 3), F(1, 3)])
    nt.assert_equal(value, F(13, 21))

def test_mean_decimals():
    value = mm.mean([D("0.5"), D("0.75"), D("0.625"), D("0.375")])
    nt.assert_equal(value, D("0.5625"))

def test_mean_iter():
    value = mm.mean(iter([1, 2, 3]))
    nt.assert_equal(value, 2)

    value = mm.mean(range(3))
    nt.assert_equal(value, 1)

def test_median():
    nt.assert_equal(mm.median([1, 3, 5]), 3)
    nt.assert_equal(mm.median([1, 3, 5, 7]), 4)

def test_median_low():
    nt.assert_equal(mm.median_low([1, 3, 5]), 3)
    nt.assert_equal(mm.median_low([1, 3, 5, 7]), 3)

@nt.raises(StatisticsError)
def test_median_low_empty():
    mm.median_low([])

def test_median_high():
    nt.assert_equal(mm.median_high([1, 3, 5]), 3)
    nt.assert_equal(mm.median_high([1, 3, 5, 7]), 5)

@nt.raises(StatisticsError)
def test_median_high_empty():
    mm.median_high([])

def test_mode():
    nt.assert_equal(mm.mode([1, 1, 2, 3, 3, 3, 3, 4]), 3)

def test_mode_strings():
    nt.assert_equal(mm.mode(["red", "blue", "blue", "red", "green", "red", "red"]), "red")

@nt.raises(StatisticsError)
def test_mode_not_unique():
    mm.mode(["red", "blue", "blue", "red"])

@nt.raises(StatisticsError)
def test_mode_empty():
    mm.mode([])

def test_variance():
    data = [2.75, 1.75, 1.25, 0.25, 0.5, 1.25, 3.5]
    nt.assert_equal(mm.variance(data), 1.3720238095238095)

def test_variance_with_mean():
    data = [2.75, 1.75, 1.25, 0.25, 0.5, 1.25, 3.5]
    mean = mm.mean(data)
    nt.assert_equal(mm.variance(data, mean), 1.3720238095238095)

def test_variance_decimals():
    value = mm.variance([D("27.5"), D("30.25"), D("30.25"), D("34.5"), D("41.75")])
    nt.assert_equal(value, D('31.01875'))

def test_variance_fractions():
    value = mm.variance([F(1, 6), F(1, 2), F(5, 3)])
    nt.assert_equal(value, F(67, 108))

def test_variance_iterator():
    nt.assert_equal(mm.variance(iter([1, 2, 5])), 4.333333333333334)

def test_pvariance():
    data = [0.0, 0.25, 0.25, 1.25, 1.5, 1.75, 2.75, 3.25]
    nt.assert_equal(mm.pvariance(data), 1.25)

def test_pvariance_with_mean():
    data = [0.0, 0.25, 0.25, 1.25, 1.5, 1.75, 2.75, 3.25]
    mean = mm.mean(data)
    nt.assert_equal(mm.pvariance(data, mean), 1.25)

def test_pvariance_decimals():
    value = mm.pvariance([D("27.5"), D("30.25"), D("30.25"), D("34.5"), D("41.75")])
    nt.assert_equal(value, D('24.815'))

def test_pvariance_fractions():
    value = mm.pvariance([F(1, 4), F(5, 4), F(1, 2)])
    nt.assert_equal(value, F(13, 72))

def test_pvariance_iterator():
    nt.assert_equal(mm.pvariance(iter([1, 2, 3])), 0.6666666666666666)

@nt.raises(StatisticsError)
def test_pvariance_empty():
    mm.pvariance([])

def test_stdev():
    value = mm.stdev([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])
    nt.assert_equal(value, 1.0810874155219827)

def test_pstddev():
    value = mm.pstdev([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])
    nt.assert_equal(value, 0.986893273527251)

def test_geometric_mean():
    cases = [
        ([1.5, 2.5, 2.5, 2.75, 3.25, 4.75], 2.7121486566834387),
        ([1.5, 2.5, 2.5, 2.75, -3.25, 4.75], 2.2284330795786698),
        ([1.5, 2.5, 2.5, 2.75, 0, 4.75], 2.63258262293452),]

    for data, expected in cases:
        fun = lambda data, expected: nt.assert_almost_equal(mm.geometric_mean(data), expected)
        yield fun, data, expected

@nt.raises(StatisticsError)
def test_geometric_mean_empty():
    mm.geometric_mean([])

def test_harmonic_mean():
    cases = [
        ([1.5, 2.5, 2.5, 2.75, 3.25, 4.75], 2.5547986710408086),
        ([1.5, 2.5, 2.5, 2.75, -3.25, 4.75], 3.4619305150494095),
        ([1.5, 2.5, 2.5, 2.75, 0, 4.75], 2.9399812441387936),]

    for data, expected in cases:
        fun = lambda data, expected: nt.assert_almost_equal(mm.harmonic_mean(data), expected)
        yield fun, data, expected

@nt.raises(StatisticsError)
def test_harmonic_mean_empty():
    mm.harmonic_mean([])

def test_skewness():
    cases = [
        ([1.5, 2.5, 2.5, 2.75, 3.25, 4.75], 0.5193819834930741),
        ([1.5, 2.5, 2.5, 2.75, -3.25, 4.75], -0.8623011014727693),
        ([1.5, 2.5, 2.5, 2.75, 0, 4.75], 0.03989169123327498),
        ([1.0, 1.0, 1.0], 0.0),
    ]

    for data, expected in cases:
        fun = lambda data, expected: nt.assert_almost_equal(mm.skewness(data), expected)
        yield fun, data, expected

@nt.raises(StatisticsError)
def test_skewness_empty():
    mm.skewness([])

def test_kurtosis():
    cases = [
        ([1.5, 2.5, 2.5, 2.75, 3.25, 4.75], -1.0485692089183762),
        ([1.5, 2.5, 2.5, 2.75, -3.25, 4.75], -0.6949222688831207),
        ([1.5, 2.5, 2.5, 2.75, 0, 4.75], -1.2034104454720884),
        ([1.0, 1.0, 1.0], 0.0),
    ]

    for data, expected in cases:
        fun = lambda data, expected: nt.assert_almost_equal(mm.kurtosis(data), expected)
        yield fun, data, expected

@nt.raises(StatisticsError)
def test_kurtosis_empty():
    mm.kurtosis([])

def test_percentile():
    cases = [
        ([1.5, 2.5, 2.5, 2.75, 3.25, 4.75], 50, 2.5),
        ([1.5, 2.5, 2.5, 2.75, 3.25, 4.75], 99, 4.75),
        ([1.5, 2.5, 2.5, 2.75, 3.25, 4.75], 10, 1.5),
    ]

    for data, confidence, expected in cases:
        fun = lambda data, confidence, expected: nt.assert_almost_equal(mm.percentile(data, confidence), expected)
        yield fun, data, confidence, expected


def test_percentile_few_points():
    with nt.assert_raises_regexp(StatisticsError, "few data points \(6\) for 1th"):
        mm.percentile([1.5, 2.5, 2.5, 2.75, 3.25, 4.75], 1)

def test_percentile_empty():
    with nt.assert_raises_regexp(StatisticsError, "few data points \(0\) for 90th"):
        mm.percentile([], 90)

def test_get_histogram():
    value = mm.get_histogram([1.5, 2.5, 2.5, 2.75, 3.25, 4.75, 5.0])
    nt.assert_equal(value, [(3.5, 5), (5.5, 2), (7.5, 0)])

    value = mm.get_histogram([1.0, 1.0, 1.0])
    nt.assert_equal(value, [(2.0, 3)])

def test_get_histogram_few_points():
    with nt.assert_raises_regexp(StatisticsError, "few data points \(1\) for get_histogram"):
        mm.get_histogram([1.5])

def test_get_histogram_bins():
    nt.assert_equal(mm.get_histogram_bins(1, 3, 0.5, 5), [2, 3, 4])

    nt.assert_equal(mm.get_histogram_bins(1, 2, -1/3.5, 1.0), [1])
