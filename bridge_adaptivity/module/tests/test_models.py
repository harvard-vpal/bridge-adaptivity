from ddt import ddt, data, unpack
from django.test import TestCase

from module import models
from module.engines.engine_mock import EngineMock
from module.engines.engine_vpal import EngineVPAL
from module.models import Engine, GradingPolicy
from module.policies.policy_points_earned import PointsEarnedGradingPolicy
from module.policies.policy_trials_count import TrialsCountGradingPolicy


class TestEngineUtilityFunction(TestCase):
    def test__discover_engines(self):
        """Test _discover_engines function."""
        found_engines = models._discover_applicable_modules(folder_name='engines', file_startswith='engine_')
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
        default_engine = Engine.get_default()
        engine_default_new_set = Engine.objects.filter(is_default=True)
        self.assertEquals(engine_default_new_set.count(), 1)
        self.assertEquals(engine_default_set.first(), default_engine)

    def test_engine_driver_property(self):
        """Test Engine model's property engine_driver."""
        host, token = 'fake_host', 'fake_token'
        engine_mock = Engine.objects.create(engine='engine_mock', engine_name='Mock')
        engine_vpal = Engine.objects.create(
            engine='engine_vpal', engine_name='VPAL', host=host, token=token
        )
        vpal_driver = engine_vpal.engine_driver
        self.assertIsInstance(engine_mock.engine_driver, EngineMock)
        self.assertIsInstance(vpal_driver, EngineVPAL)
        self.assertEqual(vpal_driver.host, host)
        self.assertEqual(vpal_driver.headers, {'Authorization': 'Token {}'.format(token)})

@ddt
class TestDiscoverGradingPolicies(TestCase):
    def test_discover_grading_policies(self):
        """Test _discover_applicable_modules function."""
        found_policies = models._discover_applicable_modules(folder_name='policies', file_startswith='policy_')
        self.assertEquals(len(found_policies), 3)
        self.assertCountEqual(
            [('policy_points_earned.py', 'points_earned'), ('policy_trials_count.py', 'trials_count'),
             ('policy_full_credit.py', 'full_credit')],
            found_policies
        )

    @unpack
    @data(
        ("module.policies.policy_", "points_earned", "GradingPolicy", "PointsEarnedGradingPolicy"),
        ("module.policies.policy_", "trials_count", "GradingPolicy", "TrialsCountGradingPolicy"),
        ("module.policies.policy_", "full_credit", "GradingPolicy", "FullCreditOnCompleteGradingPolicy"),
    )
    def test_get_policy_module(self, mod, mod_name, cls_end, exp_cls_name):
        """Test _get_grading_policy_module function."""
        grade_policy = models._get_grading_policy_cls(mod, mod_name, class_endswith=cls_end)
        self.assertEquals(grade_policy.__name__, exp_cls_name)


class TestGradingPolicyModel(TestCase):
    fixtures = ['gradingpolicy.json']

    def test_grading_policy_is_default(self):
        gp1 = GradingPolicy.objects.create(name='trials_count', public_name='GP1', is_default=True)
        gp2 = GradingPolicy.objects.create(name='trials_count', public_name='GP2', is_default=True)

        default_set = GradingPolicy.objects.filter(is_default=True)
        self.assertEquals(default_set.count(), 1)
        default_engine = default_set.first()
        self.assertNotEqual(default_engine, gp1)
        self.assertEquals(default_engine, gp2)

    def test_grading_policy_get_default_engine(self):
        """Test get_default method."""
        default_set = GradingPolicy.objects.filter(is_default=True)
        # cause we use fixtures we already have default GP on this step.
        self.assertTrue(default_set, "Default GradingPolicy should be defined in fixtures.")
        default_grading_policy = GradingPolicy.get_default()
        gp_default_new_set = GradingPolicy.objects.filter(is_default=True)
        self.assertEquals(gp_default_new_set.count(), 1)
        self.assertEquals(default_set.first(), default_grading_policy)

    def test_policy_cls_property(self):
        gp_trials_count = GradingPolicy.objects.get(name='trials_count')
        gp_points_earned = GradingPolicy.objects.get(name='points_earned')
        self.assertTrue(gp_trials_count.policy_cls is TrialsCountGradingPolicy)
        self.assertTrue(gp_points_earned.policy_cls is PointsEarnedGradingPolicy)
