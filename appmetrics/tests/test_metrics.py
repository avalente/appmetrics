import mock
from nose.tools import assert_equal, assert_in, raises, assert_is, assert_is_instance

from .. import metrics as mm, exceptions, histogram, simple_metrics as simple, meter


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

    def test_metrics(self):
        mm.REGISTRY = dict(test1=mock.Mock(), test2=mock.Mock())
        expected = ["test1", "test2"]
        assert_equal(mm.metrics(), expected)

    def test_delete_metric(self):
        m1 = mock.Mock()
        m2 = mock.Mock()
        mm.REGISTRY = dict(test1=m1, test2=m2)

        assert_equal(mm.delete_metric("test1"), m1)
        assert_equal(mm.REGISTRY, dict(test2=m2))

    def test_delete_metric_not_found(self):
        m1 = mock.Mock()
        m2 = mock.Mock()
        mm.REGISTRY = dict(test1=m1, test2=m2)

        assert_equal(mm.delete_metric("test3"), None)
        assert_equal(mm.REGISTRY, dict(test1=m1, test2=m2))

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

    def test_new_counter(self):
        metric = mm.new_counter("test")

        assert_is(metric, mm.metric("test"))

        assert_is_instance(metric, simple.Counter)

    def test_new_gauge(self):
        metric = mm.new_gauge("test")

        assert_is(metric, mm.metric("test"))

        assert_is_instance(metric, simple.Gauge)

    def test_new_meter(self):
        metric = mm.new_meter("test")

        assert_is(metric, mm.metric("test"))

        assert_is_instance(metric, meter.Meter)

