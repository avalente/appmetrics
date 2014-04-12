from nose.tools import assert_equal

from .. import simple_metrics as mm


class TestCounter(object):
    def setUp(self):
        self.obj = mm.Counter()

    def test_notify(self):
        self.obj.notify(5)
        assert_equal(self.obj.value, 5)

        self.obj.notify(-5)
        assert_equal(self.obj.value, 0)

        self.obj.notify(-1)
        assert_equal(self.obj.value, -1)

    def test_notify_not_integer(self):
        self.obj.notify(1.4)
        assert_equal(self.obj.value, 1)

    def test_get(self):
        self.obj.value = 3
        assert_equal(self.obj.get(), dict(kind="counter", value=3))

    def test_raw_data(self):
        self.obj.value = 3
        assert_equal(self.obj.raw_data(), 3)


class TestGauge(object):
    def setUp(self):
        self.obj = mm.Gauge()

    def test_notify(self):
        assert_equal(self.obj.value, None)
        self.obj.notify("version 1.0")
        assert_equal(self.obj.value, "version 1.0")

        self.obj.notify(1.23)
        assert_equal(self.obj.value, 1.23)

    def test_get(self):
        self.obj.value = "test"
        assert_equal(self.obj.get(), dict(kind="gauge", value="test"))

    def test_raw_data(self):
        self.obj.value = "test"
        assert_equal(self.obj.raw_data(), "test")
