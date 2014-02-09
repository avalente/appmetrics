import random

from nose.tools import assert_equal, raises, assert_almost_equal
import mock

from .. import histogram as mm


def test_uniform_reservoir_defaults():
    ur = mm.UniformReservoir()
    assert_equal(ur.size, mm.DEFAULT_UNIFORM_RESERVOIR_SIZE)
    assert_equal(ur._values, [0] * mm.DEFAULT_UNIFORM_RESERVOIR_SIZE)
    assert_equal(ur.values, [])
    assert_equal(ur.sorted_values, [])
    assert_equal(ur.count, 0)


class TestUniformReservoir(object):
    def setUp(self):
        self.state = random.getstate()
        random.seed(42)

        self.size = 5
        self.ur = mm.UniformReservoir(self.size)

    def tearDown(self):
        random.setstate(self.state)

    def test_add_first(self):
        self.ur.add(1.5)
        assert_equal(self.ur.values, [1.5])

        self.ur.add(2.5)
        assert_equal(self.ur.values, [1.5, 2.5])

        self.ur.add(3.5)
        assert_equal(self.ur.values, [1.5, 2.5, 3.5])

        self.ur.add(4.5)
        assert_equal(self.ur.values, [1.5, 2.5, 3.5, 4.5])

        self.ur.add(5.5)
        assert_equal(self.ur.values, [1.5, 2.5, 3.5, 4.5, 5.5])

    def test_add_overflow(self):
        for i in range(5):
            self.ur.add(i + 1.5)

        assert_equal(self.ur.values, [1.5, 2.5, 3.5, 4.5, 5.5])

        self.ur.add(10)
        assert_equal(self.ur.values, [1.5, 2.5, 3.5, 10.0, 5.5])

        self.ur.add(11)
        assert_equal(self.ur.values, [11, 2.5, 3.5, 10.0, 5.5])

        self.ur.add(12)
        assert_equal(self.ur.values, [11, 12, 3.5, 10.0, 5.5])

        self.ur.add(13)
        assert_equal(self.ur.values, [11, 13, 3.5, 10.0, 5.5])

        self.ur.add(14)
        assert_equal(self.ur.values, [11, 13, 3.5, 10.0, 5.5])

        self.ur.add(15)
        assert_equal(self.ur.values, [11, 13, 3.5, 10.0, 5.5])

    def test_values_smaller_count(self):
        for i in range(3):
            self.ur.add(i)
        assert_equal(len(self.ur.values), self.ur.count)

    def test_values_greater_count(self):
        for i in range(6):
            self.ur.add(i)
        assert_equal(len(self.ur.values), self.ur.size)

    def test_sorted_values(self):
        for i in range(5):
            self.ur.add(random.randint(1, 10))

        random.seed(42)
        assert_equal(self.ur.sorted_values, sorted(random.randint(1, 10) for i in range(5)))

    @raises(TypeError)
    def test_add_bad_type(self):
        self.ur.add(None)


class TestHistogram(object):
    def setUp(self):
        self.reservoir = mock.Mock()

        self.histogram = mm.Histogram(self.reservoir)

    def test_notify(self):
        result = self.histogram.notify(1.2)
        assert_equal(
            self.reservoir.add.call_args_list,
            [mock.call(1.2)])
        assert_equal(result, self.reservoir.add.return_value)

    def test_raw_data(self):
        result = self.histogram.raw_data()
        assert_equal(result, self.reservoir.values)

    def test_get_values_zeros(self):
        self.reservoir.sorted_values = []

        expected = dict(
            min=0,
            max=0,
            arithmetic_mean=0.0,
            geometric_mean=0.0,
            harmonic_mean=0.0,
            median=0.0,
            variance=0.0,
            standard_deviation=0.0,
            skewness=0.0,
            kurtosis=0.0,
            percentile=[(50, 0.0), (75, 0.0), (90, 0.0), (95, 0.0), (99, 0.0), (99.9, 0.0)],
            histogram=[(0, 0)],
            n=0
        )

        assert_equal(self.histogram.get(), expected)

    def test_get_values(self):
        self.reservoir.sorted_values = [1.5, 2.5, 2.5, 2.75, 3.25, 3.26, 4.75]

        res = self.histogram.get()

        assert_almost_equal(res['min'], 1.5)
        assert_almost_equal(res['max'], 4.75)
        assert_almost_equal(res['arithmetic_mean'], 2.93)
        assert_almost_equal(res['geometric_mean'], 2.784379085700406)
        assert_almost_equal(res['harmonic_mean'], 2.6362666258180956)
        assert_almost_equal(res['median'], 2.75)
        assert_almost_equal(res['variance'], 0.99513333)
        assert_almost_equal(res['standard_deviation'], 0.9975636988851055)
        assert_almost_equal(res['skewness'], 0.4329020512437358)
        assert_almost_equal(res['kurtosis'], -0.8007344003569115)
        assert_equal(res['percentile'], [(50, 2.75),
                                         (75, 3.25),
                                         (90, 3.26),
                                         (95, 4.75),
                                         (99, 4.75),
                                         (99.9, 4.75)])
        assert_equal(res['histogram'], [(3.5, 6), (5.5, 1), (7.5, 0)])
        assert_equal(res['n'], len(self.reservoir.sorted_values))

