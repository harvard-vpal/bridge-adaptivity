import datetime

from django.test import TestCase
from django.urls.base import reverse
from mock import patch
from oauthlib.common import generate_token

from bridge_lti.models import LtiContentSource, LtiLmsPlatform
from module.mixins.views import GroupEditFormMixin
from module.models import (
    Activity, BridgeUser, Collection, CollectionOrder, ContributorPermission, Engine, GradingPolicy, ModuleGroup
)

GRADING_POLICIES = (
    # value, display_name
    ('trials_count', 'Trials count', ),
    ('points_earned', 'Points earned',),
)


class BridgeTestCase(TestCase):
    fixtures = ['gradingpolicy', 'engine', 'api', 'bridge']
    group_prefix = GroupEditFormMixin.prefix
    grading_prefix = GroupEditFormMixin.grading_prefix

    def add_prefix(self, prefix='', data=None):
        """Add prefix to form data dict, which will be send as POST or GET to view."""
        data = data or {}
        return {"{}-{}".format(prefix, k): v for k, v in data.items()}

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        self.user = BridgeUser.objects.create_user(
            username='test',
            password='test',
            email='test@me.com'
        )
        self.client.login(username='test', password='test')
        # collections
        self.collection1 = Collection.objects.create(name='col1', owner=self.user)
        self.collection2 = Collection.objects.create(name='col2', owner=self.user)
        self.collection3 = Collection.objects.create(name='col3', owner=self.user)
        # grading policies
        self.trials_count = GradingPolicy.objects.get(name='trials_count')
        self.points_earned = GradingPolicy.objects.get(name='points_earned')

        self.engine = Engine.objects.create(engine='engine_mock', engine_name='mockEngine')
        self.test_cg = ModuleGroup.objects.create(name='TestColGroup', owner=self.user)

        self.collection_order1 = CollectionOrder.objects.create(
            slug="collection_order1",
            group=self.test_cg,
            collection=self.collection1,
            engine=self.engine,
            grading_policy=self.points_earned
        )
        self.collection_order3 = CollectionOrder.objects.create(
            slug="collection_order3",
            group=self.test_cg,
            collection=self.collection3,
            engine=self.engine,
            grading_policy=self.trials_count
        )

        self.group_update_data = {
            'name': "CG2",
            'owner': self.user.id,
            'description': 'Some description for a group',
        }

        self.group_post_data = self.add_prefix(self.group_prefix, self.group_update_data)

        # LtiLmsPlatform
        self.lti_lms_platform = LtiLmsPlatform.objects.create(
            consumer_name='consumer_name',
            # This method generates a valid consumer_key.
            # The valid consumer_key is used in the test for checking LTI query.
            consumer_key=generate_token(length=25),
            consumer_secret='consumer_secret',
            expiration_date=datetime.datetime.today() + datetime.timedelta(days=1),
            lms_metadata='lms_metadata'
        )


class TestCollectionList(BridgeTestCase):
    def test_without_group_slug(self):
        """Test collection list view without group slug."""
        url = reverse('module:collection-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_with_group_id(self):
        """Test collection list view with group slug."""
        url = reverse('module:collection-list', kwargs={'group_slug': self.test_cg.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class TestCollectionGroup(BridgeTestCase):
    def test_create_cg_page_works(self):
        """Test that ModuleGroup page works correctly contain valid context and response code is 200."""
        url = reverse('module:group-add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        groups_count = ModuleGroup.objects.count()
        policy_data = {'name': self.trials_count.name}
        data = {}
        data.update(self.group_post_data)
        data.update(policy_data)
        response = self.client.post(url, data=data)
        self.assertEqual(ModuleGroup.objects.count(), groups_count + 1)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.content, b'{"status": "ok"}')

    def test_cg_list(self):
        """Test ModuleGroup list page. Check that response code is 200, `groups` is in context and is not empty."""
        url = reverse('module:group-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('groups', response.context)
        self.assertIsNotNone(response.context['groups'])
        self.assertEqual(
            list(response.context['groups'].values_list('id', flat=True)),
            list(ModuleGroup.objects.filter(owner=self.user).values_list('id', flat=True))
        )

    def test_update_cg(self):
        """Test update ModuleGroup page, check that updated collection group is really updated."""
        groups_count = ModuleGroup.objects.count()

        url = reverse('module:group-change', kwargs={'group_slug': self.test_cg.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

        response = self.client.post(url, data=self.group_update_data)
        if response.status_code == 200:
            print((dict(response.context['form'].errors)))

        self.assertEqual(groups_count, ModuleGroup.objects.count())
        test_g = ModuleGroup.objects.get(id=self.test_cg.id)
        self.assertEqual(test_g.name, self.group_update_data['name'])
        self.assertEqual(test_g.description, self.group_update_data['description'])
        self.assertNotEqual(test_g.name, self.test_cg.name)
        self.assertNotEqual(test_g.description, self.test_cg.description)
        self.assertNotEqual(test_g.collections.all(), self.test_cg.collections.all())


class CollectionGroupEditGradingPolicyTest(BridgeTestCase):

    def check_group_change_page(self):
        url = reverse('module:group-change', kwargs={'group_slug': self.test_cg.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def check_update_group(self, data):
        url = reverse('module:group-change', kwargs={'group_slug': self.test_cg.slug})
        self.client.post(url, data=data)
        self.test_cg = ModuleGroup.objects.get(id=self.test_cg.id)
        self.assertEqual(self.group_update_data['name'], self.test_cg.name)


class TestCollectionGroupCollectionOrder(BridgeTestCase):

    def test_group_collection_add(self):
        """
        Test updated collection group contains all new collections.
        """
        data = {
            "collection_group-slug": "second",
            "collection_group-collection": self.collection2.id,
            "collection_group-engine": self.engine.id,
            "collection_group-grading_policy_name": "trials_count",
            "grading-name": "trials_count"
        }
        # Group is updated with three collections two of which is repeated. Collections will increase by 1
        expected_collections_count = self.test_cg.collections.count() + 1
        url = reverse('module:collection-order-add', kwargs={'group_slug': self.test_cg.slug})
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(self.test_cg.collections.count(), expected_collections_count)

    def test_group_collection_update(self):
        """
        Test updated collection group contains all new collections.
        """
        data = {
            "collection_group-slug": self.collection_order1.slug,
            "collection_group-collection": self.collection1.id,
            "collection_group-engine": self.engine.id,
            "collection_group-grading_policy_name": "trials_count",
            "grading-name": "trials_count"
        }

        # Group is updated with three collections two of which is repeated. Collections will increase by 1
        url = reverse('module:collection-order-change', kwargs={
            'collection_order_slug': self.collection_order1.slug,
        })
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            CollectionOrder.objects.get(id=self.collection_order1.id).grading_policy.name, "trials_count"
        )

    def test_group_collection_not_valid_update(self):
        """
        Test updated collection group contains all new collections.
        """
        data = {
            "collection_group-slug": self.collection_order1.slug,
            "collection_group-collection": self.collection1.id,
            "collection_group-engine": self.engine.id,
            "collection_group-grading_policy_name": "wrong_grading",
            "grading-name": "wrong_grading"
        }

        # Group is updated with three collections two of which is repeated. Collections will increase by 1
        url = reverse('module:collection-order-change', kwargs={
            'collection_order_slug': self.collection_order1.slug
        })
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors,
            {
                'grading_policy_name': [
                    'Select a valid choice. wrong_grading is not one of the available choices.',
                    'Not correct policy'
                ]
            }
        )

    def test_cg_with_not_correct_policy_engine_pair(self):
        """
        Try to create collectiongroup with not correct pair of policy and engine.

        Not correct pair example - engine graded policy with mock engine.
        In this case it should return 200, and context['form'] should contain errors.
        """
        data = {
            "collection_group-slug": self.collection_order1.slug,
            "collection_group-collection": self.collection1.id,
            "collection_group-engine": self.engine.id,
            "collection_group-grading_policy_name": "engine_grade",
        }
        url = reverse('module:collection-order-change', kwargs={
            'collection_order_slug': self.collection_order1.slug
        })
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertEqual(
            response.context['form'].errors,
            {
                'engine': ["This Engine doesn't support chosen Policy. Please choose another policy or engine."],
                'grading_policy_name': [('This policy can be used only with VPAL engine(s). '
                                         'Choose another policy or engine.')]
            }

        )

    def test_group_collection_remove(self):
        """
        Test updated collection group doesn't contain old collections.
        """
        data = [col_order for col_order, grade_update_available in self.test_cg.ordered_collections]
        expected_group_collection = len(data) - 1
        # Group is updated with one collection all existing should be removed.
        url = reverse(
            'module:collection-group-delete',
            kwargs={'collection_order_slug': self.collection_order1.slug}
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len([x for x in self.test_cg.ordered_collections]), expected_group_collection)

    def test_group_collection_reordered(self):
        """
        Test collections are reordered in the group on move to different positions command.
        """
        data = {
            "collection_group-slug": "second",
            "collection_group-collection": self.collection2.id,
            "collection_group-engine": self.engine.id,
            "collection_group-grading_policy_name": "trials_count",
            "grading-name": "trials_count"
        }
        url = reverse('module:collection-order-add', kwargs={'group_slug': self.test_cg.slug})
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 202)

        ordered_collections = [col_order for col_order, grade_update_available in self.test_cg.ordered_collections]
        expected_collection_order = [ordered_collections[2], ordered_collections[1], ordered_collections[0]]

        # Moving collection3 up, collection1 down and get reordered result as (collection3, collection2, collection1)
        move_to_index_0 = reverse('module:collection-move', kwargs={
            'collection_order_slug': ordered_collections[2].slug,
            'order': 0,
        })
        response_up = self.client.get(move_to_index_0)
        self.assertEqual(response_up.status_code, 201)
        move_to_index_2 = reverse('module:collection-move', kwargs={
            'collection_order_slug': ordered_collections[0].slug,
            'order': 2,
        })
        response_down = self.client.get(move_to_index_2)
        self.assertEqual(response_down.status_code, 201)
        ordered_collections = [col_order for col_order, grade_update_available in self.test_cg.ordered_collections]
        self.assertEqual(ordered_collections, expected_collection_order)

    def test_get_grading_policy_form(self):
        """Test that form is present in response context for both grading policies."""
        policies = GRADING_POLICIES
        for policy, _ in policies:
            url = reverse('module:grading_policy_form', kwargs={
                "collection_order_slug": self.collection_order1.slug
            }) + "?grading_policy={}".format(policy)
            response = self.client.get(url)
            self.assertIn('form', response.context)

    def test_get_not_valid_grading_policy_form(self):
        """Check that if not correct grading policy passed - no form return."""
        url = reverse('module:grading_policy_form', kwargs={
            "collection_order_slug": self.collection_order1.slug
        }) + "?grading_policy={}".format('some_policy')
        response = self.client.get(url)
        self.assertNotIn('form', response.context)


class TestBackURLMixin(BridgeTestCase):
    def setUp(self):
        super().setUp()
        self.back_url = '/test_back_url/'

    def test_collection_edit_back_url(self):
        """Test back_url param is added into context in collection change view."""
        url = (
            reverse('module:collection-change', kwargs={'slug': self.collection1.slug}) +
            '?back_url={}'.format(self.back_url)
        )
        change_response = self.client.get(url)
        self.assertIn('back_url', change_response.context)
        self.assertEqual(change_response.context['back_url'], self.back_url)

    @patch('module.views.get_available_courses', return_value=([], []))
    def test_collection_detail_back_url(self, available_course_mock):
        """Test back_url param is added into context navigation from collection detail view."""
        url_detail = (
            reverse('module:collection-detail', kwargs={'slug': self.collection1.slug}) +
            '?back_url={}'.format(self.back_url)
        )
        detail_response = self.client.get(url_detail)
        self.assertIn('back_url', detail_response.context)
        self.assertEqual(detail_response.context['back_url'], self.back_url)

    def test_collectiongroup_edit_back_url(self):
        """Test back_url param is added into context navigation from collectiongroup edit view."""
        change_url = (
            reverse('module:group-change', kwargs={'group_slug': self.test_cg.slug}) +
            '?back_url={}'.format(self.back_url)
        )
        change_response = self.client.get(change_url)
        self.assertIn('back_url', change_response.context)
        self.assertEqual(change_response.context['back_url'], self.back_url)

    def test_collectiongroup_detail_back_url(self):
        """Test back_url param is added into context navigation from collectiongroup detail view."""
        url = (
            reverse('module:group-detail', kwargs={'group_slug': self.test_cg.slug}) +
            '?back_url={}'.format(self.back_url)
        )
        detail_response = self.client.get(url)
        self.assertIn('back_url', detail_response.context)
        self.assertEqual(detail_response.context['back_url'], self.back_url)


class TestManualSync(BridgeTestCase):

    @patch('module.tasks.sync_collection_engines.delay')
    @patch('module.tasks.sync_collection_engines.apply_async')
    @patch('module.views.get_available_courses', return_value=([], []))
    def test_immediate_synchronization(
        self, mock_get_available_courses, mock_apply_async, mock_delay
    ):
        expected_url = reverse('module:collection-detail', kwargs={'slug': self.collection1.slug}) + '?back_url=None'
        url = reverse('module:collection-sync', kwargs={'slug': self.collection1.slug})
        response = self.client.get(url)
        mock_delay.assert_called_once_with(
            created_at=Collection.objects.get(slug=self.collection1.slug).updated_at,
            collection_slug=self.collection1.slug,
        )
        self.assertRedirects(response, expected_url)

    @patch('module.tasks.sync_collection_engines.delay')
    @patch('module.tasks.sync_collection_engines.apply_async')
    @patch('module.views.get_available_courses')
    def test_immediate_synchronization_incorrect_pk(
        self, mock_get_available_courses, mock_apply_async, mock_delay
    ):
        col_slug = '345'
        url = reverse('module:collection-sync', kwargs={'slug': col_slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class TestManualGradeUpdate(BridgeTestCase):

    @patch('module.tasks.update_students_grades.delay')
    def test_mandatory_students_grade_update(self, mock_delay):
        expected_url = reverse('module:group-detail', kwargs={'group_slug': self.test_cg.slug}) + '?back_url=None'
        url = reverse('module:update_grades', kwargs={'collection_order_slug': self.collection_order1.slug})
        response = self.client.get(url)
        mock_delay.assert_called_once_with(collection_order_slug=self.collection_order1.slug)
        self.assertRedirects(response, expected_url)

    def test_grade_update_with_incorect_group_slug(self):
        url = reverse('module:update_grades', kwargs={'collection_order_slug': '3'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class TestCreateUpdateActivity(BridgeTestCase):
    fixtures = BridgeTestCase.fixtures + ['api.json', 'bridge.json']

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        super().setUp()
        self.back_url = reverse('module:collection-detail', kwargs={'slug': self.collection1.slug})
        self.provider = LtiContentSource.objects.get(id=2)
        self.add_url = reverse('module:activity-add', kwargs={'collection_slug': self.collection1.slug})
        self.create_data = {
            'name': 'Adapt 310',
            'tags': '',
            'atype': 'G',
            'difficulty': '1',
            'source_launch_url': (
                'https://edx-staging-vpal.raccoongang.com/lti_lms_platform/courses/course-v1:MSFT+DAT222'
                'x+4T2017/block-v1:MSFT+DAT222x+4T2017+type@problem+block@306986fde3e2489db9c97462dca19d4b'),
            'source_name': 'Adapt 310',
            'stype': 'problem',
            'points': '0.5',
            'repetition': 1,
            'lti_content_source': self.provider.id,
        }

    @patch('module.tasks.sync_collection_engines.delay')
    @patch('module.tasks.sync_collection_engines.apply_async')
    @patch('module.views.get_available_courses')
    def test_create_activity(self, *mocks):
        activity_count = Activity.objects.count()
        response = self.client.post(self.add_url, self.create_data)
        if response.status_code == 200:
            # form errors
            print((response.context['form'].errors))
        self.assertEqual(activity_count + 1, Activity.objects.count())

    @patch('module.tasks.sync_collection_engines.delay')
    @patch('module.tasks.sync_collection_engines.apply_async')
    @patch('module.views.get_available_courses')
    def test_update_activity(self, *mocks):
        # create activity
        self.test_create_activity(*mocks)
        activity = Activity.objects.get()
        activity_count = Activity.objects.count()
        update_data = {
            'name': 'ADOPT 100500',
            'tags': 'some, tags, here',
            'stype': 'video'
        }
        data = self.create_data.copy()
        data.update(update_data)
        url = reverse('module:activity-change', kwargs={'pk': activity.id, 'collection_slug': self.collection1.slug})
        response = self.client.post(url, data)
        self.assertEqual(activity_count, Activity.objects.count())

        if response.status_code == 200:
            # form errors
            print((response.context['form'].errors))

        new_activity = Activity.objects.get()
        self.assertEqual(new_activity.name, update_data['name'])
        self.assertEqual(new_activity.tags, update_data['tags'])
        self.assertEqual(new_activity.stype, update_data['stype'])


class TestMultipleContentSources(BridgeTestCase):
    fixtures = BridgeTestCase.fixtures + ['api.json', 'bridge.json']

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        super().setUp()

    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_oauth_access_token',
           return_value=('some_token', datetime.datetime.now() + datetime.timedelta(days=1)))
    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_provider_courses',
           return_value=[{'name': 'name'} for _ in range(10)])
    @patch('api.backends.base_api_client.BaseApiClient.get_provider_courses',
           return_value=[{'name': 'name'} for _ in range(10)])
    def test_list_courses_multiple_sources(
            self,
            mock_base_get_provider_courses,
            mock_get_edx_provider_courses,
            mock_get_edx_oauth_access_token
    ):
        """
        Test count of courses from the multiple source.
        """
        url = reverse('module:collection-detail', kwargs={'slug': self.collection1.slug})
        response = self.client.get(url)
        self.assertIn('source_courses', response.context)
        self.assertTrue(response.context['source_courses'])
        total_courses = len(response.context['source_courses'])

        # we use 10 because mock function return list with size 10
        expect_course_count = LtiContentSource.objects.all().count() * 10

        self.assertEqual(total_courses, expect_course_count)

        provider = LtiContentSource.objects.all().first()
        provider.is_active = False
        provider.save()

        response = self.client.get(url)
        self.assertIn('source_courses', response.context)
        self.assertTrue(response.context['source_courses'])
        new_total_courses = len(response.context['source_courses'])

        self.assertNotEqual(new_total_courses, total_courses)
        # we use 10 because mock function return list with size 10
        self.assertEqual(new_total_courses, expect_course_count - 10)


class TestSharingModuleGroup(BridgeTestCase):

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        super().setUp()
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
        ContributorPermission.objects.create(user=self.contributor_1, group=self.test_cg)

    def test_add_contributor(self):
        url = reverse('module:group-share', kwargs={'group_slug': self.test_cg.slug})
        data = {
            "contributor_username": self.contributor_2.username
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.test_cg.contributors.filter(username=self.contributor_2.username).exists())

    def test_delete_contributor(self):
        url = reverse(
            'module:group-share-remove',
            kwargs={'group_slug': self.test_cg.slug, 'username': self.contributor_1.username}
        )
        response = self.client.get(url)
        self.assertRedirects(response, reverse('module:group-detail', kwargs={'group_slug': self.test_cg.slug}))
        self.assertFalse(self.test_cg.contributors.filter(username=self.contributor_1.username).exists())
