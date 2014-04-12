import random

from nose import tools as nt
import mock

from .. import histogram as mm
from ..py3comp import assert_items_equal

def test_uniform_reservoir_defaults():
    ur = mm.UniformReservoir()
    nt.assert_equal(ur.size, mm.DEFAULT_UNIFORM_RESERVOIR_SIZE)
    nt.assert_equal(ur._values, [0] * mm.DEFAULT_UNIFORM_RESERVOIR_SIZE)
    nt.assert_equal(ur.values, [])
    nt.assert_equal(ur.sorted_values, [])
    nt.assert_equal(ur.count, 0)


def test_search_greater():
    values = [(1, "a"), (2, "b"), (3, "c"), (4, "d"), (5, "e")]

    tests = [
        (0, 0),
        (1, 0),
        (1.5, 1),
        (2, 1),
        (4.5, 4),
        (5, 4),
        (6, 5)]

    for target, expected in tests:
        f = lambda target, expected: nt.assert_equal(expected, mm.search_greater(values, target))
        yield f, target, expected


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
        nt.assert_equal(self.ur.values, [1.5])

        self.ur.add(2.5)
        nt.assert_equal(self.ur.values, [1.5, 2.5])

        self.ur.add(3.5)
        nt.assert_equal(self.ur.values, [1.5, 2.5, 3.5])

        self.ur.add(4.5)
        nt.assert_equal(self.ur.values, [1.5, 2.5, 3.5, 4.5])

        self.ur.add(5.5)
        nt.assert_equal(self.ur.values, [1.5, 2.5, 3.5, 4.5, 5.5])

    def test_add_overflow(self):
        for i in range(5):
            self.ur.add(i + 1.5)

        nt.assert_equal(self.ur.values, [1.5, 2.5, 3.5, 4.5, 5.5])

        self.ur.add(10)
        nt.assert_equal(self.ur.values, [1.5, 2.5, 3.5, 10.0, 5.5])

        self.ur.add(11)
        nt.assert_equal(self.ur.values, [11, 2.5, 3.5, 10.0, 5.5])

        self.ur.add(12)
        nt.assert_equal(self.ur.values, [11, 12, 3.5, 10.0, 5.5])

        self.ur.add(13)
        nt.assert_equal(self.ur.values, [11, 13, 3.5, 10.0, 5.5])

        self.ur.add(14)
        nt.assert_equal(self.ur.values, [11, 13, 3.5, 10.0, 5.5])

        self.ur.add(15)
        nt.assert_equal(self.ur.values, [11, 13, 3.5, 10.0, 5.5])

    def test_values_smaller_count(self):
        for i in range(3):
            self.ur.add(i)
        nt.assert_equal(len(self.ur.values), self.ur.count)

    def test_values_greater_count(self):
        for i in range(6):
            self.ur.add(i)
        nt.assert_equal(len(self.ur.values), self.ur.size)

    def test_sorted_values(self):
        for i in range(5):
            self.ur.add(random.randint(1, 10))

        random.seed(42)
        nt.assert_equal(self.ur.sorted_values, sorted(random.randint(1, 10) for i in range(5)))

    @nt.raises(TypeError)
    def test_add_bad_type(self):
        self.ur.add(None)

    def test_same_kind(self):
        other = mm.UniformReservoir(self.ur.size)
        nt.assert_true(self.ur.same_kind(other))

    def test_same_kind_with_different_class(self):
        other = mm.SlidingWindowReservoir(self.ur.size)
        nt.assert_false(self.ur.same_kind(other))

    def test_same_kind_with_different_parameters(self):
        other = mm.UniformReservoir(10)
        nt.assert_false(self.ur.same_kind(other))


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
        nt.assert_equal(self.swr.values, [1.5])

        self.swr.add(2.5)
        nt.assert_equal(self.swr.values, [1.5, 2.5])

        self.swr.add(3.5)
        nt.assert_equal(self.swr.values, [1.5, 2.5, 3.5])

        self.swr.add(4.5)
        nt.assert_equal(self.swr.values, [1.5, 2.5, 3.5, 4.5])

        self.swr.add(5.5)
        nt.assert_equal(self.swr.values, [1.5, 2.5, 3.5, 4.5, 5.5])

    def test_add_overflow(self):
        for i in range(5):
            self.swr.add(i + 1.5)

        nt.assert_equal(self.swr.values, [1.5, 2.5, 3.5, 4.5, 5.5])

        self.swr.add(10)
        nt.assert_equal(self.swr.values, [2.5, 3.5, 4.5, 5.5, 10.0])

        self.swr.add(11)
        nt.assert_equal(self.swr.values, [3.5, 4.5, 5.5, 10.0, 11.0])

    def test_sorted_values(self):
        for i in range(5):
            self.swr.add(random.randint(1, 10))

        random.seed(42)
        nt.assert_equal(self.swr.sorted_values, sorted(random.randint(1, 10) for i in range(5)))

    @nt.raises(TypeError)
    def test_add_bad_type(self):
        self.swr.add(None)

    def test_same_kind(self):
        other = mm.SlidingWindowReservoir(self.swr.size)
        nt.assert_true(self.swr.same_kind(other))

    def test_same_kind_with_different_class(self):
        other = mm.UniformReservoir(self.swr.size)
        nt.assert_false(self.swr.same_kind(other))

    def test_same_kind_with_different_parameters(self):
        other = mm.SlidingWindowReservoir(10)
        nt.assert_false(self.swr.same_kind(other))


class TestSlidingTimeWindowReservoir(object):
    def setUp(self):
        self.patch = mock.patch('appmetrics.histogram.time.time')
        self.time = self.patch.start()

        self.window_size = 3 # seconds
        self.rr = mm.SlidingTimeWindowReservoir(self.window_size)

    def tearDown(self):
        self.patch.stop()

    @nt.raises(TypeError)
    def test_add_bad_type(self):
        self.rr.add(None)

    def test_add(self):
        self.time.return_value = 1.0

        for i in range(10):
            self.rr.add(i)

        nt.assert_equal(list(self.rr._values), [(1.0, float(x)) for x in range(10)])

    def test_add_exceeded_time(self):
        self.time.return_value = 1
        self.rr.add(1)

        nt.assert_equal(list(self.rr._values), [(1, 1)])

        self.time.return_value = 1.1
        self.rr.add(2)
        nt.assert_equal(list(self.rr._values), [(1, 1), (1.1, 2)])

        self.time.return_value = 1.2
        self.rr.add(3)
        nt.assert_equal(list(self.rr._values), [(1, 1), (1.1, 2), (1.2, 3)])

        self.time.return_value = 1.3
        self.rr.add(4)
        nt.assert_equal(list(self.rr._values), [(1, 1), (1.1, 2), (1.2, 3), (1.3, 4)])

        self.time.return_value = 3.1
        self.rr.add(5)
        nt.assert_equal(list(self.rr._values), [(1, 1), (1.1, 2), (1.2, 3), (1.3, 4), (3.1, 5)])

        self.time.return_value = 4.05
        self.rr.add(6)
        nt.assert_equal(list(self.rr._values), [(1.1, 2), (1.2, 3), (1.3, 4), (3.1, 5), (4.05, 6)])

        self.time.return_value = 4.1
        self.rr.add(7)
        nt.assert_equal(list(self.rr._values), [(1.1, 2), (1.2, 3), (1.3, 4), (3.1, 5), (4.05, 6), (4.1, 7)])

        self.time.return_value = 4.2
        self.rr.add(8)
        nt.assert_equal(list(self.rr._values), [(1.3, 4), (3.1, 5), (4.05, 6), (4.1, 7), (4.2, 8)])

        self.time.return_value = 10
        self.rr.add(9)
        nt.assert_equal(list(self.rr._values), [(10, 9)])

    def test_values(self):
        self.rr._values = [(1, 10), (1.5, 1.5), (2, 2), (3, 3)]
        self.time.return_value = 3.0
        nt.assert_equal(self.rr.values, [10, 1.5, 2, 3])

    def test_values_exceeded_time(self):
        self.rr._values = [(1, 10), (2, 2), (3, 1), (4, 4)]
        self.time.return_value = 4.0001
        nt.assert_equal(self.rr.values, [2, 1, 4])

    def test_sorted_values(self):
        self.rr._values = [(1, 10), (2, 2), (3, 1), (4, 4)]
        self.time.return_value = 4.0001
        nt.assert_equal(self.rr.sorted_values, [1, 2, 4])

    def test_same_kind(self):
        other = mm.SlidingTimeWindowReservoir(self.rr.window_size)
        nt.assert_true(self.rr.same_kind(other))

    def test_same_kind_with_different_class(self):
        other = mm.UniformReservoir(self.rr.window_size)
        nt.assert_false(self.rr.same_kind(other))

    def test_same_kind_with_different_parameters(self):
        other = mm.SlidingTimeWindowReservoir(10)
        nt.assert_false(self.rr.same_kind(other))


class TestExponentialDecayingReservoir(object):
    def setUp(self):
        self.patch = mock.patch('appmetrics.histogram.time.time', mock.Mock(return_value=0))
        self.time = self.patch.start()

        self.state = random.getstate()
        random.seed(42)

        self.size = 5
        self.rr = mm.ExponentialDecayingReservoir(self.size)

    def tearDown(self):
        self.patch.stop()
        random.setstate(self.state)

    @nt.raises(TypeError)
    def test_add_bad_type(self):
        self.rr.add(None)

    def _add_after(self, value, time):
        self.time.return_value += time
        self.rr.add(value)
        return self.rr.values

    def test_add_first(self):
        nt.assert_equal(self._add_after(1.5, 1), [1.5])
        nt.assert_equal(self._add_after(2.5, 1), [1.5, 2.5])
        nt.assert_equal(self._add_after(3.5, 1), [1.5, 3.5, 2.5])
        nt.assert_equal(self._add_after(4.5, 1), [1.5, 3.5, 4.5, 2.5])
        nt.assert_equal(self._add_after(5.5, 1), [5.5, 1.5, 3.5, 4.5, 2.5])

    def test_add_overflow(self):
        for i in range(1, 6):
            self._add_after(0.5+i, 1)

        nt.assert_equal(self._add_after(10, 1), [1.5, 10.0, 3.5, 4.5, 2.5])
        nt.assert_equal(self._add_after(20, 1), [1.5, 10.0, 3.5, 4.5, 2.5])
        nt.assert_equal(self._add_after(30, 1), [10.0, 3.5, 4.5, 30.0,  2.5])

    def test_rescaling(self):
        for i in range(1, 6):
            self._add_after(0.5+i, 1)

        # this should trigger a rescaling, so all the old values will have very small times
        # and all the new ones will be inserted
        self._add_after(10, 3600.0)
        for i in range(1, 5):
            self._add_after(10+i, 1)

        assert_items_equal(self.rr.values, [10, 11, 12, 13, 14])

    def test_long_delay(self):
        for i in range(1, 6):
            self._add_after(0.5+i, 1)

        # this emulates a new value after 15 hours: in that case the times are too small and collapse to zero
        nt.assert_equal(self._add_after(10, 3600.0*15), [2.5, 10.0])

    def test_sorted_values(self):
        self.rr._values = [(1, 10), (2, 2), (3, 1), (4, 4)]
        nt.assert_equal(self.rr.sorted_values, [1, 2, 4, 10])

    def test_same_kind(self):
        other = mm.ExponentialDecayingReservoir(self.rr.size)
        nt.assert_true(self.rr.same_kind(other))

    def test_same_kind_with_different_class(self):
        other = mm.UniformReservoir(self.rr.size)
        nt.assert_false(self.rr.same_kind(other))

    def test_same_kind_with_different_parameters(self):
        other = mm.ExponentialDecayingReservoir(10)
        nt.assert_false(self.rr.same_kind(other))

    def test_same_kind_with_different_parameters_2(self):
        other = mm.ExponentialDecayingReservoir(self.rr.size, 1)
        nt.assert_false(self.rr.same_kind(other))


class TestHistogram(object):
    def setUp(self):
        self.reservoir = mock.Mock()

        self.histogram = mm.Histogram(self.reservoir)

    def test_notify(self):
        result = self.histogram.notify(1.2)
        nt.assert_equal(
            self.reservoir.add.call_args_list,
            [mock.call(1.2)])
        nt.assert_equal(result, self.reservoir.add.return_value)

    def test_raw_data(self):
        result = self.histogram.raw_data()
        nt.assert_equal(result, self.reservoir.values)

    def test_get_values_zeros(self):
        self.reservoir.sorted_values = []

        expected = dict(
            kind="histogram",
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

        nt.assert_equal(self.histogram.get(), expected)

    def test_get_values(self):
        self.reservoir.sorted_values = [1.5, 2.5, 2.5, 2.75, 3.25, 3.26, 4.75]

        res = self.histogram.get()

        nt.assert_equal(res['kind'], "histogram")

        nt.assert_almost_equal(res['min'], 1.5)
        nt.assert_almost_equal(res['max'], 4.75)
        nt.assert_almost_equal(res['arithmetic_mean'], 2.93)
        nt.assert_almost_equal(res['geometric_mean'], 2.784379085700406)
        nt.assert_almost_equal(res['harmonic_mean'], 2.6362666258180956)
        nt.assert_almost_equal(res['median'], 2.75)
        nt.assert_almost_equal(res['variance'], 0.99513333)
        nt.assert_almost_equal(res['standard_deviation'], 0.9975636988851055)
        nt.assert_almost_equal(res['skewness'], 0.4329020512437358)
        nt.assert_almost_equal(res['kurtosis'], -0.8007344003569115)
        nt.assert_equal(res['percentile'], [(50, 2.75),
                                         (75, 3.25),
                                         (90, 3.26),
                                         (95, 4.75),
                                         (99, 4.75),
                                         (99.9, 4.75)])
        nt.assert_equal(res['histogram'], [(3.5, 6), (5.5, 1), (7.5, 0)])
        nt.assert_equal(res['n'], len(self.reservoir.sorted_values))

