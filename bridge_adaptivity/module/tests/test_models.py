from ddt import data, ddt, unpack
from django.conf import settings
from django.test import TestCase
from mock.mock import patch

from bridge_lti.models import LtiProvider, LtiUser
from module import models
from module.engines.engine_mock import EngineMock
from module.engines.engine_vpal import EngineVPAL
from module.models import (
    Activity, BridgeUser, Collection, CollectionGroup, Engine, GradingPolicy, Sequence, SequenceItem
)
from module.policies.policy_full_credit import FullCreditOnCompleteGradingPolicy
from module.policies.policy_points_earned import PointsEarnedGradingPolicy
from module.policies.policy_trials_count import TrialsCountGradingPolicy


class TestEngineUtilityFunction(TestCase):
    def test__discover_engines(self):
        """Test _discover_engines function."""
        found_engines = models._discover_applicable_modules(folder_name='engines', file_startswith='engine_')
        self.assertEquals(len(found_engines), 2)
        self.assertCountEqual([('engine_mock', 'mock'), ('engine_vpal', 'vpal')], found_engines)

    def test__get_engine_driver(self):
        """Test _get_engine_driver function."""
        driver = models._load_cls_from_applicable_module('module.engines', 'engine_mock', class_startswith='Engine')
        self.assertEquals(driver.__name__, 'EngineMock')

        vpal_driver = models._load_cls_from_applicable_module('module.engines', 'engine_vpal',
                                                              class_startswith='Engine')
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
            [('policy_points_earned', 'points_earned'), ('policy_trials_count', 'trials_count'),
             ('policy_full_credit', 'full_credit')],
            found_policies
        )

    @unpack
    @data(
        ("module.policies", "policy_points_earned", "GradingPolicy", "PointsEarnedGradingPolicy"),
        ("module.policies", "policy_trials_count", "GradingPolicy", "TrialsCountGradingPolicy"),
        ("module.policies", "policy_full_credit", "GradingPolicy", "FullCreditOnCompleteGradingPolicy"),
    )
    def test_get_policy_module(self, mod, mod_name, cls_end, exp_cls_name):
        """Test _get_grading_policy_module function."""
        grade_policy = models._load_cls_from_applicable_module(mod, mod_name, class_endswith=cls_end)
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
        gp_full_credit = GradingPolicy.objects.get(name='full_credit')
        self.assertTrue(gp_trials_count.policy_cls is TrialsCountGradingPolicy)
        self.assertTrue(gp_points_earned.policy_cls is PointsEarnedGradingPolicy)
        self.assertTrue(gp_full_credit.policy_cls is FullCreditOnCompleteGradingPolicy)


@ddt
class TestActivityModel(TestCase):
    fixtures = ['gradingpolicy.json', 'engine.json']

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        self.user = BridgeUser.objects.create_user(
            username='test',
            password='test',
            email='test@me.com'
        )
        self.consumer = LtiProvider.objects.create(
            consumer_name='name',
            consumer_key='key',
            consumer_secret='secret',
        )
        self.lti_user = LtiUser.objects.create(
            user_id='some_user', course_id='some_course', email=self.user.email,
            lti_consumer=self.consumer, bridge_user=self.user
        )
        # collections
        self.collection1 = Collection.objects.create(name='col1', owner=self.user)
        # grading policies
        self.trials_count = GradingPolicy.objects.get(name='trials_count')
        self.points_earned = GradingPolicy.objects.get(name='points_earned')
        self.engine = Engine.objects.create(engine='engine_mock')
        self.test_cg = CollectionGroup.objects.create(
            name='TestColGroup',
            owner=self.user,
            engine=self.engine,
            grading_policy=self.points_earned
        )
        self.test_cg.collections.add(self.collection1)
        self.sequence = Sequence.objects.create(
            lti_user=self.lti_user, collection=self.collection1, group=self.test_cg
        )

    @unpack
    @data({'stype': 'video', 'is_problem': False},
          {'stype': 'html', 'is_problem': False},
          {'stype': 'problem', 'is_problem': True},
          )
    @patch('module.tasks.sync_collection_engines.apply_async')
    def test_is_problem_property(self, mock_apply_async, stype, is_problem):
        activity = Activity(name='test', collection=self.collection1, tags='test', atype='G', stype=stype)
        self.assertEqual(activity.is_problem, is_problem)

    @unpack
    @data({'stype': 'video', 'is_problem': False},
          {'stype': 'html', 'is_problem': False},
          {'stype': 'problem', 'is_problem': True},
          )
    @patch('module.tasks.sync_collection_engines.apply_async')
    def test_create_sequence_item_for_activity(self, mock_apply_async, stype, is_problem):
        activity = Activity.objects.create(
            name='test', collection=self.collection1, tags='test', atype='G', stype=stype
        )
        sequence_item = SequenceItem.objects.create(
            sequence=self.sequence,
            activity=activity,
        )
        self.assertTrue(sequence_item.is_problem == activity.is_problem)
        self.assertEqual(sequence_item.is_problem, is_problem)

    @patch('module.tasks.sync_collection_engines.apply_async')
    def test_update_sequence_item_with_grade(self, mock_apply_async):
        activity = Activity.objects.create(
            name='test', collection=self.collection1, tags='test', atype='G', stype='problem'
        )
        mock_apply_async.assert_called_once_with(
            kwargs={'collection_id': self.collection1.id, 'created_at': self.collection1.updated_at},
            countdown=settings.CELERY_DELAY_SYNC_TASK,
        )
        sequence_item = SequenceItem.objects.create(
            sequence=self.sequence,
            activity=activity,
        )
        sequence_item.score = 0.5
        sequence_item.save()
        # save() method is overloaded in the models, and we test that it works correctly
        self.assertEqual(sequence_item.score, 0.5)


class TestCollectionGroupModel(TestCase):
    fixtures = ['gradingpolicy.json', 'engine.json']

    def test_create_empty_group(self):
        """Test an ability to create empty collection group (without collections)."""
        groups_count = CollectionGroup.objects.count()
        user = BridgeUser.objects.create_user(
            username='test',
            password='test',
            email='test@me.com'
        )
        points_earned = GradingPolicy.objects.get(name='points_earned')
        engine = Engine.objects.create(engine='engine_mock')
        group = CollectionGroup.objects.create(
            name='some name', engine=engine, grading_policy=points_earned, owner=user
        )
        self.assertEqual(CollectionGroup.objects.count(), groups_count + 1)
        self.assertFalse(group.collections.all())
