from ddt import data, ddt, unpack
from django.conf import settings
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _
from mock.mock import patch
from multiselectfield.db.fields import MSFList

from bridge_lti.models import LtiLmsPlatform, LtiUser, OutcomeService
from module import models
from module.engines.engine_mock import EngineMock
from module.engines.engine_vpal import EngineVPAL
from module.models import (
    Activity, BridgeUser, Collection, CollectionOrder, ContributorPermission, Engine, GradingPolicy, ModuleGroup,
    Sequence, SequenceItem
)
from module.policies.policy_full_credit import FullCreditOnCompleteGradingPolicy
from module.policies.policy_points_earned import PointsEarnedGradingPolicy
from module.policies.policy_trials_count import TrialsCountGradingPolicy

OPTIONS = {
    'AT': _('Questions viewed/total'),
    'EP': _('Earned grade'),
    'RW': _('Answers right/wrong'),
}


class TestEngineUtilityFunction(TestCase):
    def test__discover_engines(self):
        """Test _discover_engines function."""
        found_engines = models._discover_applicable_modules(folder_name='engines', file_startswith='engine_')
        self.assertEqual(len(found_engines), 2)
        self.assertCountEqual([('engine_mock', 'mock'), ('engine_vpal', 'vpal')], found_engines)

    def test__get_engine_driver(self):
        """Test _get_engine_driver function."""
        driver = models._load_cls_from_applicable_module('module.engines', 'engine_mock', class_startswith='Engine')
        self.assertEqual(driver.__name__, 'EngineMock')

        vpal_driver = models._load_cls_from_applicable_module('module.engines', 'engine_vpal',
                                                              class_startswith='Engine')
        self.assertEqual(vpal_driver.__name__, 'EngineVPAL')


class TestEngineModel(TestCase):
    def test_engine__is_default(self):
        """Test default engine is always only one."""
        engine_default_old = Engine.objects.create(engine='engine_mock', engine_name='Mock Old', is_default=True)
        engine_default_new = Engine.objects.create(engine='engine_mock', engine_name='Mock New', is_default=True)
        default_set = Engine.objects.filter(is_default=True)
        self.assertEqual(default_set.count(), 1)
        default_engine = default_set.first()
        self.assertNotEqual(default_engine, engine_default_old)
        self.assertEqual(default_engine, engine_default_new)

    def test_engine_get_default_engine(self):
        """Test get_default_engine method."""
        engine_default_set = Engine.objects.filter(is_default=True)
        self.assertFalse(engine_default_set)
        default_engine = Engine.get_default()
        engine_default_new_set = Engine.objects.filter(is_default=True)
        self.assertEqual(engine_default_new_set.count(), 1)
        self.assertEqual(engine_default_set.first(), default_engine)

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
        self.assertEqual(len(found_policies), 4)
        self.assertCountEqual(
            [('policy_engine_grade', 'engine_grade'), ('policy_points_earned', 'points_earned'),
             ('policy_trials_count', 'trials_count'), ('policy_full_credit', 'full_credit')],
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
        self.assertEqual(grade_policy.__name__, exp_cls_name)


class TestGradingPolicyModel(TestCase):
    fixtures = ['gradingpolicy.json']

    def test_grading_policy_is_default(self):
        gp1 = GradingPolicy.objects.create(name='trials_count', public_name='GP1', is_default=True)
        gp2 = GradingPolicy.objects.create(name='trials_count', public_name='GP2', is_default=True)

        default_set = GradingPolicy.objects.filter(is_default=True)
        self.assertEqual(default_set.count(), 1)
        default_engine = default_set.first()
        self.assertNotEqual(default_engine, gp1)
        self.assertEqual(default_engine, gp2)

    def test_grading_policy_get_default_engine(self):
        """Test get_default method."""
        default_set = GradingPolicy.objects.filter(is_default=True)
        # cause we use fixtures we already have default GP on this step.
        self.assertTrue(default_set, "Default GradingPolicy should be defined in fixtures.")
        default_grading_policy = GradingPolicy.get_default()
        gp_default_new_set = GradingPolicy.objects.filter(is_default=True)
        self.assertEqual(gp_default_new_set.count(), 1)
        self.assertEqual(default_set.first(), default_grading_policy)

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
        self.consumer = LtiLmsPlatform.objects.create(
            consumer_name='name',
            consumer_key='key',
            consumer_secret='secret',
        )
        self.lti_user = LtiUser.objects.create(
            user_id='some_user', course_id='some_course', email=self.user.email,
            lti_lms_platform=self.consumer, bridge_user=self.user
        )
        # collections
        self.collection1 = Collection.objects.create(name='col1', owner=self.user)
        # grading policies
        self.trials_count = GradingPolicy.objects.get(name='trials_count')
        self.points_earned = GradingPolicy.objects.get(name='points_earned')
        self.engine = Engine.objects.create(engine='engine_mock')
        self.test_cg = ModuleGroup.objects.create(
            name='TestColGroup',
            owner=self.user,
        )

        self.collection_order = CollectionOrder.objects.create(
            group=self.test_cg,
            collection=self.collection1,
            engine=self.engine,
            grading_policy=self.points_earned
        )

        self.sequence = Sequence.objects.create(
            lti_user=self.lti_user, collection_order=self.collection_order, suffix='12345'
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
    def test_sequence_item_user(self, apply_async):
        activity = Activity.objects.create(
            name='test', collection=self.collection1, tags='test', atype='G', stype='html'
        )
        sequence_item = SequenceItem.objects.create(
            sequence=self.sequence,
            activity=activity,
            suffix='68686'
        )
        self.assertEqual(
            f'{self.sequence.lti_user.user_id}{self.sequence.suffix}{sequence_item.suffix}',
            sequence_item.user_id_for_consumer
        )

    @patch('module.tasks.sync_collection_engines.apply_async')
    def test_update_sequence_item_with_grade(self, mock_apply_async):
        activity = Activity.objects.create(
            name='test', collection=self.collection1, tags='test', atype='G', stype='problem'
        )
        mock_apply_async.assert_called_once_with(
            kwargs={'collection_slug': self.collection1.slug, 'created_at': self.collection1.updated_at},
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
        groups_count = ModuleGroup.objects.count()
        user = BridgeUser.objects.create_user(
            username='test',
            password='test',
            email='test@me.com'
        )
        group = ModuleGroup.objects.create(
            name='some name', owner=user
        )
        self.assertEqual(ModuleGroup.objects.count(), groups_count + 1)
        self.assertFalse(group.collections.all())


class TestDeleteObjectsSeparately(TestCase):
    fixtures = ['gradingpolicy.json', 'engine.json']

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        self.user = BridgeUser.objects.create_user(
            username='test',
            password='test',
            email='test@me.com'
        )
        self.consumer = LtiLmsPlatform.objects.create(
            consumer_name='name',
            consumer_key='key',
            consumer_secret='secret',
        )
        # collections
        self.collection1 = Collection.objects.create(name='col1', owner=self.user)
        # grading policies
        self.trials_count = GradingPolicy.objects.get(name='trials_count')
        self.points_earned = GradingPolicy.objects.get(name='points_earned')
        self.engine = Engine.objects.create(engine='engine_mock')
        self.test_cg = ModuleGroup.objects.create(
            name='TestColGroup',
            owner=self.user,
        )
        # self.test_cg.collections.add(self.collection1)
        self.collection_orer = CollectionOrder.objects.create(
            group=self.test_cg,
            collection=self.collection1,
            engine=self.engine,
            grading_policy=self.points_earned,
        )

    def test_delete_group(self):
        collections_count = Collection.objects.count()
        self.test_cg.delete()
        # check that any collection was deleted
        self.assertEqual(Collection.objects.count(), collections_count)


@ddt
class TestSequence(TestCase):
    fixtures = ['gradingpolicy.json', 'engine.json']

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        self.user = BridgeUser.objects.create_user(
            username='test_user',
            password='test_pass',
            email='test@test.com'
        )
        self.collection = Collection.objects.create(name='testcol1', owner=self.user)

        self.source_launch_url = 'http://test_source_launch_url.com'
        self.activity = Activity.objects.create(
            name='testactivity1', collection=self.collection, source_launch_url=self.source_launch_url
        )
        self.activity2 = Activity.objects.create(
            name='testactivity2',
            collection=self.collection,
            source_launch_url=f"{self.source_launch_url}2",
            stype='problem',
        )
        self.activity3 = Activity.objects.create(
            name='testactivity3', collection=self.collection, source_launch_url=f"{self.source_launch_url}3",
        )
        self.activity4 = Activity.objects.create(
            name='testactivity4',
            collection=self.collection,
            source_launch_url=f"{self.source_launch_url}4",
            stype='problem',
        )
        self.activity5 = Activity.objects.create(
            name='testactivity5',
            collection=self.collection,
            source_launch_url=f"{self.source_launch_url}5",
            stype='problem',
        )
        self.lti_lms_platform = LtiLmsPlatform.objects.create(
            consumer_name='test_consumer', consumer_key='test_consumer_key', consumer_secret='test_consumer_secret'
        )
        self.lti_user = LtiUser.objects.create(
            user_id='test_user_id', lti_lms_platform=self.lti_lms_platform, bridge_user=self.user
        )
        self.engine = Engine.objects.get(engine='engine_mock')
        self.grading_policy = GradingPolicy.objects.get(name='points_earned')
        self.outcome_service = OutcomeService.objects.create(
            lis_outcome_service_url='test_url', lms_lti_connection=self.lti_lms_platform
        )

        self.test_cg = ModuleGroup.objects.create(
            name='TestColGroup',
            owner=self.user,
        )

        self.collection_order = CollectionOrder.objects.create(
            group=self.test_cg,
            collection=self.collection,
            engine=self.engine,
            grading_policy=self.grading_policy
        )

        self.sequence = Sequence.objects.create(
            lti_user=self.lti_user,
            collection_order=self.collection_order,
            outcome_service=self.outcome_service
        )
        self.sequence_item_1 = SequenceItem.objects.create(sequence=self.sequence, activity=self.activity, score=0.4)
        self.sequence_item_2 = SequenceItem.objects.create(sequence=self.sequence, activity=self.activity2, score=0.6)
        self.sequence_item_3 = SequenceItem.objects.create(sequence=self.sequence, activity=self.activity3)
        self.sequence_item_4 = SequenceItem.objects.create(sequence=self.sequence, activity=self.activity4, score=0)

    @unpack
    @data(
        # NOTE(idegtiarov) because of switching to using of MultiSelectField - option should be saved as MSFList
        #  from the multiselectfield.db.fields
        {'option': MSFList(OPTIONS, ['AT']), 'expected_result': ['Questions viewed/total: 4/5']},
        {'option': MSFList(OPTIONS, ['EP', 'AT', 'RW']), 'expected_result': [
            'Earned grade: 30.0%', 'Questions viewed/total: 4/5', 'Answers right/wrong: 2/1'
        ]},
        {'option': MSFList(OPTIONS, []), 'expected_result': []},
    )
    def test_sequence_ui_details(self, option, expected_result):
        self.collection_order.ui_option = option
        self.collection_order.save()
        details = self.sequence.sequence_ui_details()
        self.assertEqual(expected_result, details)


class TestContributorPermission(TestCase):

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        self.user = BridgeUser.objects.create_user(
            username='test_user',
            password='test_pass',
            email='test@test.com'
        )
        self.contributor_1 = BridgeUser.objects.create_user(
            username='test_contributor_1',
            password='test_contributor_1',
            email='test_contributor_1@test.com'
        )
        self.contributor_2 = BridgeUser.objects.create_user(
            username='contributor_2',
            password='contributor_2',
            email='contributor_2@test.com'
        )
        self.test_cg = ModuleGroup.objects.create(
            name='TestColGroup',
            owner=self.user,
        )
        self.contributor_1_permisson = ContributorPermission.objects.create(user=self.contributor_1, group=self.test_cg)

    def test_create_contributor_permission(self):
        cp = ContributorPermission.objects.create(user=self.contributor_2, group=self.test_cg)
        cp.save()
        self.assertTrue(self.test_cg.contributors.filter(username=self.contributor_2.username).exists())

    def test_delete_contributor_permission(self):
        self.contributor_1_permisson.delete()
        self.assertFalse(self.test_cg.contributors.filter(username=self.contributor_1.username).exists())
