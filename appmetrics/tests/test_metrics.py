import mock
from nose.tools import assert_equal, assert_in, raises, assert_is, assert_is_instance, assert_false, assert_true

from .. import metrics as mm, exceptions, histogram, simple_metrics as simple, meter


class TestMetricsModule(object):
    def setUp(self):
        self.original_registy = mm.REGISTRY.copy()
        self.original_tags = mm.TAGS.copy()

        mm.REGISTRY.clear()
        mm.TAGS.clear()

    def tearDown(self):
        mm.REGISTRY.clear()
        mm.REGISTRY.update(self.original_registy)

        mm.TAGS.clear()
        mm.TAGS.update(self.original_tags)

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

    def test_get(self):
        mm.REGISTRY = dict(test1=mock.Mock(), test2=mock.Mock())
        assert_equal(mm.get("test1"), mm.REGISTRY["test1"].get.return_value)

    @raises(exceptions.InvalidMetricError)
    def test_get_not_existing(self):
        mm.REGISTRY = dict(test1=mock.Mock(), test2=mock.Mock())
        mm.get("test3")

    def test_notify(self):
        mm.REGISTRY = dict(test1=mock.Mock(), test2=mock.Mock())
        mm.notify("test1", 123)
        assert_equal(
            mm.REGISTRY["test1"].notify.call_args_list,
            [mock.call(123)]
        )

    @raises(exceptions.InvalidMetricError)
    def test_notify_not_existing(self):
        mm.REGISTRY = dict(test1=mock.Mock(), test2=mock.Mock())
        mm.notify("test3", 123)

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

    def test_delete_metric_with_tags(self):
        mm.TAGS = {"test": {"test1", "test3"}}

        m1 = mock.Mock()
        m2 = mock.Mock()
        m3 = mock.Mock()
        mm.REGISTRY = dict(test1=m1, test2=m2, test3=m3)

        assert_equal(mm.delete_metric("test1"), m1)
        assert_equal(mm.REGISTRY, dict(test2=m2, test3=m3))

        assert_equal(mm.TAGS["test"], {"test3"})

    def test_new_histogram_default(self):
        metric = mm.new_histogram("test")

        assert_is(metric, mm.metric("test"))

        assert_is_instance(metric, histogram.Histogram)
        assert_is_instance(metric.reservoir, histogram.UniformReservoir)
        assert_equal(metric.reservoir.size, histogram.DEFAULT_UNIFORM_RESERVOIR_SIZE)

    def test_new_histogram(self):
        metric = mm.new_histogram("test", histogram.UniformReservoir(10))

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

    @raises(exceptions.InvalidMetricError)
    def test_new_reservoir_bad_type(self):
        mm.new_reservoir('xxx')

    @raises(TypeError)
    def test_new_reservoir_bad_args(self):
        mm.new_reservoir('uniform', xxx='yyy')

    def test_new_reservoir_with_defaults(self):
        reservoir = mm.new_reservoir()
        assert_is_instance(reservoir, histogram.UniformReservoir)
        assert_equal(reservoir.size, histogram.DEFAULT_UNIFORM_RESERVOIR_SIZE)

    def test_new_reservoir(self):
        reservoir = mm.new_reservoir('sliding_window', 5)
        assert_is_instance(reservoir, histogram.SlidingWindowReservoir)
        assert_equal(reservoir.size, 5)

    def test_new_histogram_with_implicit_reservoir(self):
        metric = mm.new_histogram_with_implicit_reservoir('test', 'sliding_window', 5)
        assert_is_instance(metric, histogram.Histogram)
        assert_is_instance(metric.reservoir, histogram.SlidingWindowReservoir)
        assert_equal(metric.reservoir.size, 5)

    @mock.patch('appmetrics.metrics.time')
    def test_with_histogram(self, time):
        # emulate the time spent in the function by patching time.time() and returning
        # two known values.
        times = [5, 3.4]
        time.time.side_effect = times.pop

        # decorated function
        @mm.with_histogram("test")
        def fun(v1, v2):
            """a docstring"""

            return v1+v2

        assert_equal(fun.__doc__, "a docstring")

        res = fun(1, 2)
        assert_equal(res, 3)

        assert_equal(mm.metric("test").raw_data(), [1.6])

    @mock.patch('appmetrics.metrics.time')
    def test_with_histogram_with_method(self, time):
        # emulate the time spent in the function by patching time.time() and returning
        # two known values.
        times = [5, 3.4]
        time.time.side_effect = times.pop

        # decorated method
        class MyClass(object):
            def __init__(self, v1):
                self.v1 = v1

            @mm.with_histogram("test")
            def method(self, v2):
                """a docstring"""

                return self.v1+v2

        assert_equal(MyClass.method.__doc__, "a docstring")

        obj = MyClass(1)

        assert_equal(obj.method.__doc__, "a docstring")

        res = obj.method(2)
        assert_equal(res, 3)

        assert_equal(mm.metric("test").raw_data(), [1.6])

    def test_with_histogram_multiple(self):
        @mm.with_histogram("test")
        def f1(v1, v2):
            """a docstring"""

            return v1+v2

        @mm.with_histogram("test")
        def f2(v1, v2):
            """another docstring"""

            return v1*v2

        assert_equal(f1.__doc__, "a docstring")
        assert_equal(f2.__doc__, "another docstring")

        res = f1(1, 2)
        assert_equal(res, 3)

        res = f2(2, 3)
        assert_equal(res, 6)

        assert_equal(len(mm.metric("test").raw_data()), 2)

    @raises(exceptions.InvalidMetricError)
    def test_with_histogram_bad_reservoir_type(self):
        # decorated function
        @mm.with_histogram("test", "xxx")
        def fun(v1, v2):
            """a docstring"""

            return v1+v2

    @raises(exceptions.DuplicateMetricError)
    def test_with_histogram_multiple_and_arguments(self):
        @mm.with_histogram("test")
        def f1(v1, v2):
            """a docstring"""

            return v1+v2

        @mm.with_histogram("test", size=100)
        def f2(v1, v2):
            """another docstring"""

            return v1*v2

    @raises(exceptions.DuplicateMetricError)
    def test_with_histogram_multiple_different_type(self):
        mm.new_gauge("test")

        @mm.with_histogram("test")
        def f2(v1, v2):
            """another docstring"""

            return v1*v2

    def test_with_meter(self):

        @mm.with_meter("test")
        def fun(v):
            """a docstring"""

            return v*2

        assert_equal(fun.__doc__, "a docstring")

        res = [fun(i) for i in range(6)]
        assert_equal(res, [0, 2, 4, 6, 8, 10])

        assert_equal(mm.metric("test").raw_data(), 6)

    def test_with_meter_with_method(self):

        class MyClass(object):
            def __init__(self, v):
                self.v = v

            @mm.with_meter("test")
            def m1(self, v):
                """a docstring"""

                return v*self.v

            @mm.with_meter("test")
            def m2(self, v):
                """another docstring"""

                return v+self.v

        assert_equal(MyClass.m1.__doc__, "a docstring")
        assert_equal(MyClass.m2.__doc__, "another docstring")

        obj = MyClass(2)

        res = [obj.m1(i) for i in range(3)]
        assert_equal(res, [0, 2, 4])

        res = [obj.m2(i) for i in range(3)]
        assert_equal(res, [2, 3, 4])

        assert_equal(mm.metric("test").raw_data(), 6)

    def test_with_meter_multiple(self):
        @mm.with_meter("test")
        def f1(v1, v2):
            """a docstring"""

            return v1+v2

        @mm.with_meter("test")
        def f2(v1, v2):
            """another docstring"""

            return v1*v2

        assert_equal(f1.__doc__, "a docstring")
        assert_equal(f2.__doc__, "another docstring")

        res = f1(1, 2)
        assert_equal(res, 3)

        res = f2(2, 3)
        assert_equal(res, 6)

        assert_equal(mm.metric("test").raw_data(), 2)

    @raises(exceptions.DuplicateMetricError)
    def test_with_meter_multiple_and_arguments(self):
        @mm.with_meter("test")
        def f1(v1, v2):
            """a docstring"""

            return v1+v2

        @mm.with_meter("test", tick_interval=100)
        def f2(v1, v2):
            """another docstring"""

            return v1*v2

    @raises(exceptions.DuplicateMetricError)
    def test_with_meter_multiple_different_type(self):
        mm.new_gauge("test")

        @mm.with_meter("test")
        def f2(v1, v2):
            """another docstring"""

            return v1*v2

    @raises(exceptions.InvalidMetricError)
    def test_tag_invalid_name(self):
        mm.tag("test", "test")

    def test_tag(self):
        m1 = mock.Mock()
        m2 = mock.Mock()
        m3 = mock.Mock()

        mm.REGISTRY = {"test1": m1, "test2": m2, "test3": m3}
        mm.tag("test1", "1")
        mm.tag("test3", "1")
        mm.tag("test2", "2")

        assert_equal(mm.TAGS, {"1": {"test1", "test3"}, "2": {"test2"}})

    def test_tags(self):
        mm.TAGS = {"1": {"test1", "test3"}, "2": {"test2"}}

        assert_equal(mm.tags(), mm.TAGS)
        assert_false(mm.tags() is mm.TAGS)

    def test_untag_bad_tag(self):
        mm.TAGS = {"1": {"test1", "test3"}, "2": {"test2"}}

        assert_false(mm.untag("test1", "xxx"))

    def test_untag_bad_metric(self):
        mm.TAGS = {"1": {"test1", "test3"}, "2": {"test2"}}

        assert_false(mm.untag("xxx", "1"))

    def test_untag(self):
        mm.TAGS = {"1": {"test1", "test3"}, "2": {"test2"}}

        assert_true(mm.untag("test1", "1"))

        assert_equal(mm.TAGS, {"1": {"test3"}, "2": {"test2"}})

    def test_untag_last_group(self):
        mm.TAGS = {"1": {"test1", "test3"}, "2": {"test2"}}

        assert_true(mm.untag("test1", "1"))
        assert_true(mm.untag("test3", "1"))

        assert_equal(mm.TAGS, {"2": {"test2"}})

    def test_metrics_by_tag_invalid_tag(self):
        mm.TAGS = {"1": {"test1", "test3"}, "2": {"test2"}}

        assert_equal(mm.metrics_by_tag("test"), {})

    def test_metrics_by_tag(self):
        m1 = mock.Mock()
        m2 = mock.Mock()
        m3 = mock.Mock()

        mm.REGISTRY = {"test1": m1, "test2": m2, "test3": m3}
        mm.TAGS = {"1": {"test1", "test3"}, "2": {"test3"}}

        assert_equal(mm.metrics_by_tag("1"), {"test1": m1.get(), "test3": m3.get()})

    def test_metrics_by_tag_deletion_while_looping(self):
        m1 = mock.Mock()
        m2 = mock.Mock()
        m3 = mock.Mock()

        m2.get.side_effect = exceptions.InvalidMetricError

        mm.REGISTRY = {"test1": m1, "test2": m2, "test3": m3}
        mm.TAGS = {"1": {"test1", "test2", "test3"}, "2": {"test2"}}


        assert_equal(mm.metrics_by_tag("1"), {"test1": m1.get(), "test3": m3.get()})

    def test_metrics_by_name_list(self):
        mm.REGISTRY = dict(test1=mock.Mock(), test2=mock.Mock(), test3=mock.Mock())
        out = mm.metrics_by_name_list(["test1", "test3"])
        expected = {'test1': mm.REGISTRY["test1"].get.return_value,
                    'test3': mm.REGISTRY["test3"].get.return_value}

        assert_equal(out, expected)

