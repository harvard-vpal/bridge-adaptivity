from django.test import TestCase

from module import models
from module.engines.engine_mock import EngineMock
from module.engines.engine_vpal import EngineVPAL
from module.models import Engine


class TestEngineUtilityFunction(TestCase):
    def test__discover_engines(self):
        """Test _discover_engines function."""
        found_engines = models._discover_engines()
        self.assertEquals(len(found_engines), 2)
        self.assertCountEqual([('engine_mock.py', 'mock'), ('engine_vpal.py', 'vpal')], found_engines)

    def test__get_engine_driver(self):
        """Test _get_engine_driver function."""
        driver = models._get_engine_driver('engine_mock')
        self.assertEquals(driver.__name__, 'EngineMock')

        vpal_driver = models._get_engine_driver('engine_vpal')
        self.assertEquals(vpal_driver.__name__, 'EngineVPAL')


class TestEngineModel(TestCase):
    def test_engine__is_default(self):
        """Test default engine is always only one."""
        engine_default_old = Engine.objects.create(engine='engine_mock', engine_name='Mock Old', is_default=True)
        engine_default_new = Engine.objects.create(engine='engine_mock', engine_name='Mock New', is_default=True)
        default_set = Engine.objects.filter(is_default=True)
        self.assertEquals(default_set.count(), 1)
        default_engine = default_set.first()
        self.assertNotEqual(default_engine, engine_default_old)
        self.assertEquals(default_engine, engine_default_new)

    def test_engine_get_default_engine(self):
        """Test get_default_engine method."""
        engine_default_set = Engine.objects.filter(is_default=True)
        self.assertFalse(engine_default_set)
        default_engine = Engine.get_default_engine()
        engine_default_new_set = Engine.objects.filter(is_default=True)
        self.assertEquals(engine_default_new_set.count(), 1)
        self.assertEquals(engine_default_set.first(), default_engine)

    def test_engine_driver_property(self):
        """Test Engine model's property engine_driver."""
        host, token = ('fake_host', 'fake_token')
        engine_mock = Engine.objects.create(engine='engine_mock', engine_name='Mock')
        engine_vpal = Engine.objects.create(
            engine='engine_vpal', engine_name='VPAL', host=host, token=token
        )
        vpal_driver = engine_vpal.engine_driver
        self.assertIsInstance(engine_mock.engine_driver, EngineMock)
        self.assertIsInstance(vpal_driver, EngineVPAL)
        self.assertEqual(vpal_driver.host, host)
        self.assertEqual(vpal_driver.headers, {'Authorization': 'Token {}'.format(token)})
