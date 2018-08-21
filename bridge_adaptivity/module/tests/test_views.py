import datetime
import uuid

from django.test import TestCase
from django.urls.base import reverse
from mock import patch

from bridge_lti.models import LtiConsumer, LtiProvider
from module.mixins.views import GroupEditFormMixin
from module.models import Activity, BridgeUser, Collection, CollectionGroup, Course, Engine, GradingPolicy

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
        self.test_cg = CollectionGroup.objects.create(
            name='TestColGroup',
            owner=self.user,
            engine=self.engine,
            grading_policy=self.points_earned
        )
        self.test_cg.collections.add(self.collection1)
        self.test_cg.collections.add(self.collection3)

        self.course = Course.objects.create(name='test_course', owner=self.user)

        self.group_update_data = {
            'name': "CG2",
            'collections': [self.collection1.id, self.collection2.id, self.collection3.id],
            'engine': self.engine.id,
            'owner': self.user.id,
            'grading_policy_name': 'trials_count',
            'description': 'Some description for a group',
            'course': self.course.id,
        }

        self.group_post_data = self.add_prefix(self.group_prefix, self.group_update_data)

        # LtiProvider
        self.lti_provider = LtiProvider.objects.create(
            consumer_name='consumer_name',
            consumer_key='consumer_key',
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

    def test_with_group_slug(self):
        """Test collection list view with group slug."""
        url = reverse('module:collection-list', kwargs={'group_slug': self.test_cg.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class TestCollectionGroup(BridgeTestCase):
    def test_create_cg_page_works(self):
        """Test that CollectionGroup page works correctly contain valid context and response code is 200."""
        url = reverse('module:group-add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        groups_count = CollectionGroup.objects.count()
        policy_data = self.add_prefix(self.grading_prefix, {
            'threshold': 1,
            'name': self.trials_count.name,
        })
        data = {}
        data.update(self.group_post_data)
        data.update(policy_data)
        response = self.client.post(url, data=data)
        self.assertEqual(CollectionGroup.objects.count(), groups_count + 1)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.content, b'{"status": "ok"}')

    def test_cg_with_not_correct_policy_engine_pair(self):
        """
        Try to create collectiongroup with not correct pair of policy and engine.

        Not correct pair example - engine graded policy with mock engine.
        In this case it should return 200, and context['form'] should contain errors.
        """
        self.group_update_data = {
            'name': "CG2",
            'collections': [self.collection1.id, self.collection2.id, self.collection3.id],
            'engine': self.engine.id,  # mock engine
            'owner': self.user.id,
            'grading_policy_name': 'engine_grade',
            'description': 'Some description for a group',
            'course': self.course.id,
        }
        url = reverse('module:group-add')
        self.group_post_data = self.add_prefix(self.group_prefix, self.group_update_data)
        response = self.client.post(url, data=self.group_post_data)
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

    def test_cg_list(self):
        """Test CollectionGroup list page. Check that response code is 200, `groups` is in context and is not empty."""
        url = reverse('module:group-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('groups', response.context)
        self.assertIsNotNone(response.context['groups'])
        self.assertEqual(
            list(response.context['groups'].values_list('slug', flat=True)),
            list(CollectionGroup.objects.filter(owner=self.user).values_list('slug', flat=True))
        )

    def test_update_cg(self):
        """Test update CollectionGroup page, check that updated collection group is really updated."""
        groups_count = CollectionGroup.objects.count()

        url = reverse('module:group-change', kwargs={'group_slug': self.test_cg.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('grading_policy_form', response.context)
        self.assertIn('form', response.context)

        policy_data = self.add_prefix(self.grading_prefix, {
            'threshold': 1,
            'name': self.group_update_data['grading_policy_name'],
        })
        data = {}
        data.update(self.group_post_data)
        data.update(policy_data)

        response = self.client.post(url, data=data)
        if response.status_code == 200:
            print((dict(response.context['form'].errors)))

        self.assertEqual(groups_count, CollectionGroup.objects.count())
        test_g = CollectionGroup.objects.get(id=self.test_cg.id)
        self.assertEqual(test_g.name, self.group_update_data['name'])
        self.assertEqual(test_g.description, self.group_update_data['description'])
        self.assertEqual(test_g.engine.id, self.group_update_data['engine'])
        self.assertNotEqual(test_g.name, self.test_cg.name)
        self.assertNotEqual(test_g.description, self.test_cg.description)
        self.assertNotEqual(test_g.collections.all(), self.test_cg.collections.all())

    def test_add_group_to_course(self):
        self.assertIsNone(CollectionGroup.objects.get(id=self.test_cg.id).course)
        self.client.post(
            path=reverse('module:add-group-to-course', kwargs={'course_slug': self.course.slug}),
            data={'groups': self.test_cg.id}
        )
        self.assertIsNotNone(CollectionGroup.objects.get(id=self.test_cg.id).course)

    def test_remove_group_from_course(self):
        self.test_cg.course = self.course
        self.test_cg.save()
        self.assertIsNotNone(CollectionGroup.objects.get(id=self.test_cg.id).course)
        self.client.post(
            path=reverse(
                'module:rm-group-from-course',
                kwargs={
                    'course_slug': self.course.slug,
                    'group_slug': self.test_cg.slug,
                })
        )
        self.assertIsNone(CollectionGroup.objects.get(id=self.test_cg.id).course)


class CollectionGroupEditGradingPolicyTest(BridgeTestCase):
    def test_get_grading_policy_form_no_group(self):
        """Test that form is present in response context for both grading policies."""
        policies = GRADING_POLICIES
        for policy, _ in policies:
            url = reverse('module:grading_policy_form', kwargs={}) + "?grading_policy={}".format(policy)
            response = self.client.get(url)
            self.assertIn('form', response.context)

    def test_get_not_valid_grading_policy_form(self):
        """Check that if not correct grading policy passed - no form return."""
        url = reverse('module:grading_policy_form', kwargs={}) + "?grading_policy={}".format('some_policy')
        response = self.client.get(url)
        self.assertNotIn('form', response.context)

    def check_group_change_page(self):
        url = reverse('module:group-change', kwargs={'group_slug': self.test_cg.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('grading_policy_form', response.context)
        self.assertIn('form', response.context)

    def check_update_group(self, data):
        url = reverse('module:group-change', kwargs={'group_slug': self.test_cg.slug})
        self.client.post(url, data=data)
        grading_policy_count = GradingPolicy.objects.all().count()

        self.assertEqual(grading_policy_count, GradingPolicy.objects.all().count())

        self.test_cg = CollectionGroup.objects.get(id=self.test_cg.id)

        self.assertEqual(self.group_post_data[self.group_prefix + '-name'], self.test_cg.name)
        self.assertEqual(self.test_cg.grading_policy, self.points_earned)
        self.assertNotEqual(self.test_cg.grading_policy, self.trials_count)

    def test_update_grading_policy(self):
        """Test update grading policy (positive flow).

        Check that:
        * after update policy changed,
        * policy count not changed,
        * grading_policy_form is in context with default policy by default.
        """
        policies = GRADING_POLICIES
        for policy, _ in policies:
            self.group_post_data.update({'grading_policy_name': policy})

            policy_data = self.add_prefix(self.grading_prefix, {
                'threshold': 1,
                'name': policy
            })
            data = {}
            data.update(self.group_post_data)
            data.update(policy_data)

            self.check_group_change_page()
            self.check_update_group(data)

    def test_update_grading_policy_not_correct_policy(self):
        """Test update grading policy with not correct grading policy name (negative flow)."""
        self.group_post_data.update({'group-grading_policy_name': 'BLA_BLA'})

        policy_data = self.add_prefix(self.grading_prefix, {
            'threshold': 1,
            'name': 'BLA_BLA'
        })
        data = {}
        data.update(self.group_post_data)
        data.update(policy_data)

        url = reverse('module:group-change', kwargs={'group_slug': self.test_cg.slug})
        response = self.client.post(url, data=data)

        self.assertNotEqual(self.group_post_data[self.group_prefix + '-name'], self.test_cg.name)
        # check that grading policy not changed
        self.assertEqual(self.test_cg.grading_policy, self.points_earned)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIsNotNone(response.context['form'].errors)
        self.assertIn('grading_policy_name', response.context['form'].errors)


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

    @patch('module.views.get_available_courses', return_value=[])
    def test_collection_detail_back_url(self, available_course_mock):
        """Test back_url param is added into context navigation from collection detail view."""
        url_detail = (
            reverse('module:collection-detail', kwargs={'pk': self.collection1.id}) +
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


class TestCourseViews(BridgeTestCase):
    """Test case for course read/create/update/delete views."""

    def setUp(self):
        super().setUp()

        self.other_user = BridgeUser.objects.create(
            username='test2',
            password='test',
            email='test2@me.com'
        )

    def test_collectiongroup_form_course_choices(self):
        # test that self.other_course not in form choices
        url = reverse('module:group-add')
        self.other_course = Course.objects.create(
            owner=self.other_user,
            name='something',
        )
        response = self.client.get(url)
        self.assertIn('form', response.context)
        flat_course_ids = [val for val, _ in response.context['form'].fields['course'].choices if val != '']
        self.assertNotIn(self.other_course.id, flat_course_ids)

    def test_view_course_details(self):
        url = reverse('module:course-change', kwargs={'course_slug': self.course.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('course', response.context)
        self.assertEqual(response.context['course'], self.course)

    def test_view_not_mine_course_details(self):
        self.course.owner = self.other_user
        self.course.save()
        url = reverse('module:course-change', kwargs={'course_slug': self.course.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_list_courses(self):
        url = reverse('module:course-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('courses', response.context)
        self.assertIn(self.course, response.context['courses'])

    def test_create_course(self):
        url = reverse('module:course-add')
        data = {
            'name': 'Some new course',
            'description': 'bla bla bla',
            'owner': self.user.id
        }
        courses_count = Course.objects.count()
        self.client.post(url, data=data)
        self.assertNotEqual(Course.objects.count(), courses_count)

    def test_update_course(self):
        url = reverse('module:course-change', kwargs={'course_slug': self.course.slug})
        data = {
            'name': 'Some new course 111',
            'description': 'bla bla bla 1111',
            'owner': self.user.id
        }
        courses_count = Course.objects.count()
        self.client.post(url, data=data)
        self.assertEqual(Course.objects.count(), courses_count)
        course = Course.objects.get(id=self.course.id)
        self.assertEqual(course.name, data['name'])
        self.assertEqual(course.description, data['description'])

    def test_delete_course(self):
        url = reverse('module:course-delete', kwargs={'course_slug': self.course.slug})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('module:course-list'))
        self.assertFalse(Course.objects.all())

    def test_delete_not_mine_course(self):
        self.course.owner = self.other_user
        self.course.save()
        url = reverse('module:course-delete', kwargs={'course_slug': self.course.slug})
        response = self.client.get(url)
        # response should be 404 and object should not be deleted
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Course.objects.all())

    def test_update_not_mine_course(self):
        self.course.owner = self.other_user
        self.course.save()
        url = reverse('module:course-change', kwargs={'course_slug': self.course.slug})
        data = {
            'name': 'Some new course 111',
            'description': 'bla bla bla 1111',
            'owner': self.user.id
        }
        response = self.client.post(url, data=data)
        course = Course.objects.get(id=self.course.id)
        # course should not be changed
        self.assertEqual(response.status_code, 404)
        self.assertEqual(course.owner, self.other_user)
        self.assertEqual(course, self.course)
        self.assertEqual(course.name, self.course.name)
        self.assertEqual(course.description, self.course.description)
        self.assertEqual(course.owner, self.course.owner)


class TestManualSync(BridgeTestCase):

    @patch('module.tasks.sync_collection_engines.delay')
    @patch('module.tasks.sync_collection_engines.apply_async')
    @patch('module.views.get_available_courses')
    def test_immediate_synchronization(
        self, mock_get_available_courses, mock_apply_async, mock_delay
    ):
        col_slug = self.collection1.slug
        expected_url = reverse('module:collection-detail', kwargs={'pk': self.collection1.id}) + '?back_url=None'
        url = reverse('module:collection-sync', kwargs={'slug': col_slug})
        response = self.client.get(url)
        mock_delay.assert_called_once_with(
            collection_slug=str(col_slug),
            created_at=Collection.objects.get(slug=col_slug).updated_at
        )
        self.assertRedirects(response, expected_url)

    @patch('module.tasks.sync_collection_engines.delay')
    @patch('module.tasks.sync_collection_engines.apply_async')
    @patch('module.views.get_available_courses')
    def test_immediate_synchronization_incorrect_pk(
        self, mock_get_available_courses, mock_apply_async, mock_delay
    ):
        col_slug = 345
        url = reverse('module:collection-sync', kwargs={'slug': col_slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class TestManualGradeUpdate(BridgeTestCase):

    @patch('module.tasks.update_students_grades.delay')
    def test_mandatory_students_grade_update(self, mock_delay):
        group_slug = self.test_cg.slug
        expected_url = reverse('module:group-detail', kwargs={'group_slug': group_slug}) + '?back_url=None'
        url = reverse('module:update_grades', kwargs={'group_slug': group_slug})
        response = self.client.get(url)
        mock_delay.assert_called_once_with(group_id=self.test_cg.id)
        self.assertRedirects(response, expected_url)

    def test_grade_update_with_incorect_group_slug(self):
        group_slug = uuid.uuid4()
        url = reverse('module:update_grades', kwargs={'group_slug': group_slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class TestCreateUpdateActivity(BridgeTestCase):
    fixtures = BridgeTestCase.fixtures + ['api.json', 'bridge.json']

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        super().setUp()
        self.back_url = reverse('module:collection-detail', kwargs={'pk': self.collection1.id})
        self.provider = LtiConsumer.objects.get(id=2)
        self.add_url = reverse('module:activity-add', kwargs={'collection_slug': self.collection1.slug})
        self.create_data = {
            'name': 'Adapt 310',
            'tags': '',
            'atype': 'G',
            'difficulty': '1',
            'source_launch_url': (
                'https://edx-staging-vpal.raccoongang.com/lti_provider/courses/course-v1:MSFT+DAT222'
                'x+4T2017/block-v1:MSFT+DAT222x+4T2017+type@problem+block@306986fde3e2489db9c97462dca19d4b'),
            'source_name': 'Adapt 310',
            'stype': 'problem',
            'points': '0.5',
            'repetition': 1,
            'lti_consumer': self.provider.id,
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
        url = reverse('module:collection-detail', kwargs={'pk': self.collection1.id})
        response = self.client.get(url)
        self.assertIn('source_courses', response.context)
        self.assertTrue(response.context['source_courses'])
        total_courses = len(response.context['source_courses'])

        # we use 10 because mock function return list with size 10
        expect_course_count = LtiConsumer.objects.all().count() * 10

        self.assertEqual(total_courses, expect_course_count)

        provider = LtiConsumer.objects.all().first()
        provider.is_active = False
        provider.save()

        response = self.client.get(url)
        self.assertIn('source_courses', response.context)
        self.assertTrue(response.context['source_courses'])
        new_total_courses = len(response.context['source_courses'])

        self.assertNotEqual(new_total_courses, total_courses)
        # we use 10 because mock function return list with size 10
        self.assertEqual(new_total_courses, expect_course_count - 10)
