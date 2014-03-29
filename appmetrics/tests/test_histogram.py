import random
import operator

from nose.tools import assert_equal, raises, assert_almost_equal, assert_true, assert_false
import mock

from .. import histogram as mm


def test_uniform_reservoir_defaults():
    ur = mm.UniformReservoir()
    assert_equal(ur.size, mm.DEFAULT_UNIFORM_RESERVOIR_SIZE)
    assert_equal(ur._values, [0] * mm.DEFAULT_UNIFORM_RESERVOIR_SIZE)
    assert_equal(ur.values, [])
    assert_equal(ur.sorted_values, [])
    assert_equal(ur.count, 0)


class TestSortedList(object):
    def setUp(self):
        self.sl = mm.SortedList()

    def test_append(self):
        self.sl.append(1)
        self.sl.append(2)
        self.sl.append(0)

        assert_equal(self.sl._data, [0, 1, 2])

    def test_default_key(self):
        self.sl.append((0, 2, 1))
        self.sl.append((1, 1, 1))
        self.sl.append((2, 3, 1))

        assert_equal(self.sl._data, [(0, 2, 1), (1, 1, 1), (2, 3, 1)])

    def test_key(self):
        self.sl.key = operator.itemgetter(1)

        self.sl.append((0, 2, 1))
        self.sl.append((1, 1, 1))
        self.sl.append((2, 3, 1))

        assert_equal(self.sl._data, [(1, 1, 1), (0, 2, 1), (2, 3, 1)])

    def test_init(self):
        sl = mm.SortedList([1, 2, 3], key=mock.sentinel)
        assert_equal(sl._data, [1, 2, 3])
        assert_equal(sl.key, mock.sentinel)

    def test_iter(self):
        self.sl.append(1)
        self.sl.append(2)
        self.sl.append(0)

        assert_equal(list(self.sl), [0, 1, 2])

    def test_slice(self):
        self.sl.append(1)
        self.sl.append(2)
        self.sl.append(0)

        assert_equal(self.sl[:2], [0, 1])
        assert_equal(self.sl[1:], [1, 2])
        assert_equal(self.sl[0:1], [0])


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

    def test_same_kind(self):
        other = mm.UniformReservoir(self.ur.size)
        assert_true(self.ur.same_kind(other))

    def test_same_kind_with_different_class(self):
        other = mm.SlidingWindowReservoir(self.ur.size)
        assert_false(self.ur.same_kind(other))

    def test_same_kind_with_different_parameters(self):
        other = mm.UniformReservoir(10)
        assert_false(self.ur.same_kind(other))


class TestSlidingWindowReservoir(object):
    def setUp(self):
        self.state = random.getstate()
        random.seed(42)

        self.size = 5
        self.swr = mm.SlidingWindowReservoir(self.size)

    def tearDown(self):
        random.setstate(self.state)

    def test_add_first(self):
        self.swr.add(1.5)
        assert_equal(self.swr.values, [1.5])

        self.swr.add(2.5)
        assert_equal(self.swr.values, [1.5, 2.5])

        self.swr.add(3.5)
        assert_equal(self.swr.values, [1.5, 2.5, 3.5])

        self.swr.add(4.5)
        assert_equal(self.swr.values, [1.5, 2.5, 3.5, 4.5])

        self.swr.add(5.5)
        assert_equal(self.swr.values, [1.5, 2.5, 3.5, 4.5, 5.5])

    def test_add_overflow(self):
        for i in range(5):
            self.swr.add(i + 1.5)

        assert_equal(self.swr.values, [1.5, 2.5, 3.5, 4.5, 5.5])

        self.swr.add(10)
        assert_equal(self.swr.values, [2.5, 3.5, 4.5, 5.5, 10.0])

        self.swr.add(11)
        assert_equal(self.swr.values, [3.5, 4.5, 5.5, 10.0, 11.0])

    def test_sorted_values(self):
        for i in range(5):
            self.swr.add(random.randint(1, 10))

        random.seed(42)
        assert_equal(self.swr.sorted_values, sorted(random.randint(1, 10) for i in range(5)))

    @raises(TypeError)
    def test_add_bad_type(self):
        self.swr.add(None)

    def test_same_kind(self):
        other = mm.SlidingWindowReservoir(self.swr.size)
        assert_true(self.swr.same_kind(other))

    def test_same_kind_with_different_class(self):
        other = mm.UniformReservoir(self.swr.size)
        assert_false(self.swr.same_kind(other))

    def test_same_kind_with_different_parameters(self):
        other = mm.SlidingWindowReservoir(10)
        assert_false(self.swr.same_kind(other))


class TestSlidingTimeWindowReservoir(object):
    def setUp(self):
        self.patch = mock.patch('appmetrics.histogram.time.time')
        self.time = self.patch.start()

        self.window_size = 3 # seconds
        self.rr = mm.SlidingTimeWindowReservoir(self.window_size)

    def tearDown(self):
        self.patch.stop()

    @raises(TypeError)
    def test_add_bad_type(self):
        self.rr.add(None)

    def test_add(self):
        self.time.return_value = 1.0

        for i in range(10):
            self.rr.add(i)

        assert_equal(list(self.rr._values), [(1.0, float(x)) for x in range(10)])

    def test_add_exceeded_time(self):
        self.time.return_value = 1
        self.rr.add(1)

        assert_equal(list(self.rr._values), [(1, 1)])

        self.time.return_value = 1.1
        self.rr.add(2)
        assert_equal(list(self.rr._values), [(1, 1), (1.1, 2)])

        self.time.return_value = 1.2
        self.rr.add(3)
        assert_equal(list(self.rr._values), [(1, 1), (1.1, 2), (1.2, 3)])

        self.time.return_value = 1.3
        self.rr.add(4)
        assert_equal(list(self.rr._values), [(1, 1), (1.1, 2), (1.2, 3), (1.3, 4)])

        self.time.return_value = 3.1
        self.rr.add(5)
        assert_equal(list(self.rr._values), [(1, 1), (1.1, 2), (1.2, 3), (1.3, 4), (3.1, 5)])

        self.time.return_value = 4.05
        self.rr.add(6)
        assert_equal(list(self.rr._values), [(1.1, 2), (1.2, 3), (1.3, 4), (3.1, 5), (4.05, 6)])

        self.time.return_value = 4.1
        self.rr.add(7)
        assert_equal(list(self.rr._values), [(1.1, 2), (1.2, 3), (1.3, 4), (3.1, 5), (4.05, 6), (4.1, 7)])

        self.time.return_value = 4.2
        self.rr.add(8)
        assert_equal(list(self.rr._values), [(1.3, 4), (3.1, 5), (4.05, 6), (4.1, 7), (4.2, 8)])

    def test_values(self):
        self.rr._values = [(1, 10), (1.5, 1.5), (2, 2), (3, 3)]
        self.time.return_value = 3.0
        assert_equal(self.rr.values, [10, 1.5, 2, 3])

    def test_values_exceeded_time(self):
        self.rr._values = [(1, 10), (2, 2), (3, 1), (4, 4)]
        self.time.return_value = 4.0001
        assert_equal(self.rr.values, [2, 1, 4])

    def test_sorted_values(self):
        self.rr._values = [(1, 10), (2, 2), (3, 1), (4, 4)]
        self.time.return_value = 4.0001
        assert_equal(self.rr.sorted_values, [1, 2, 4])

    def test_same_kind(self):
        other = mm.SlidingTimeWindowReservoir(self.rr.window_size)
        assert_true(self.rr.same_kind(other))

    def test_same_kind_with_different_class(self):
        other = mm.UniformReservoir(self.rr.window_size)
        assert_false(self.rr.same_kind(other))

    def test_same_kind_with_different_parameters(self):
        other = mm.SlidingTimeWindowReservoir(10)
        assert_false(self.rr.same_kind(other))


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

