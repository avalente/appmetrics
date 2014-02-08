import mock
from nose.tools import assert_equal, assert_in, raises, assert_is, assert_is_instance

from .. import metrics as mm, exceptions, histogram


class TestMetricsModule(object):
    def setUp(self):
        self.original_registy = mm.REGISTRY.copy()

    def tearDown(self):
        mm.REGISTRY.clear()
        mm.REGISTRY.update(self.original_registy)

    def test_new_metric(self):
        Cls = mock.Mock()

        args = [mock.Mock(), mock.Mock()]
        kwargs = dict(other=mock.Mock())

        res = mm.new_metric("test", Cls, *args, **kwargs)

        assert_in("test", mm.REGISTRY)

        item = mm.REGISTRY["test"]
        assert_equal(
            Cls.call_args_list,
            [mock.call(*args, **kwargs)]
        )
        assert_equal(item, Cls())
        assert_equal(item, res)

    @raises(exceptions.DuplicateMetricError)
    def test_new_metric_duplicated(self):
        Cls = mock.Mock()

        mm.new_metric("test", Cls)
        mm.new_metric("test", Cls)

    @raises(exceptions.InvalidMetricError)
    def test_metric_not_found(self):
        mm.metric("test")

    def test_metric(self):
        expected = mm.REGISTRY["test"] = mock.Mock()
        assert_equal(mm.metric("test"), expected)

    def test_new_histogram_default(self):
        metric = mm.new_histogram("test")

        assert_is(metric, mm.metric("test"))

        assert_is_instance(metric, histogram.Histogram)
        assert_is_instance(metric.reservoir, histogram.UniformReservoir)
        assert_equal(metric.reservoir.size, histogram.DEFAULT_UNIFORM_RESERVOIR_SIZE)

    def test_new_histogram(self):
        metric = mm.new_histogram("test", 10)

        assert_is(metric, mm.metric("test"))

        assert_is_instance(metric, histogram.Histogram)
        assert_is_instance(metric.reservoir, histogram.UniformReservoir)
        assert_equal(metric.reservoir.size, 10)

