from django.test import TestCase
from django.urls.base import reverse
from mock import patch

from module.mixins.views import GroupEditFormMixin
from module.models import BridgeUser, Collection, CollectionGroup, Course, Engine, GradingPolicy


GRADING_POLICIES = (
    # value, display_name
    ('trials_count', 'Trials count', ),
    ('points_earned', 'Points earned',),
)


class BridgeTestCase(TestCase):
    fixtures = ['gradingpolicy', 'engine']
    group_prefix = GroupEditFormMixin.prefix
    grading_prefix = GroupEditFormMixin.grading_prefix

    def add_prefix(self, prefix='', data={}):
        """Add prefix to form data dict, which will be send as POST or GET to view."""
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

        self.engine = Engine.objects.create(engine='engine_mock')
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
        self.assertEqual(response.status_code, 302)

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
            print dict(response.context['form'].errors)

        self.assertRedirects(response, reverse('module:group-detail', kwargs={'group_slug': self.test_cg.slug}))
        self.assertEqual(groups_count, CollectionGroup.objects.count())
        test_g = CollectionGroup.objects.get(id=self.test_cg.id)
        self.assertEqual(test_g.name, self.group_update_data['name'])
        self.assertEqual(test_g.description, self.group_update_data['description'])
        self.assertEqual(test_g.engine.id, self.group_update_data['engine'])
        self.assertNotEqual(test_g.name, self.test_cg.name)
        self.assertNotEqual(test_g.description, self.test_cg.description)
        self.assertNotEqual(test_g.collections.all(), self.test_cg.collections.all())


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
        response = self.client.post(url, data=data)
        grading_policy_count = GradingPolicy.objects.all().count()

        self.assertEqual(grading_policy_count, GradingPolicy.objects.all().count())

        self.test_cg = CollectionGroup.objects.get(id=self.test_cg.id)

        self.assertEqual(self.group_post_data[self.group_prefix + '-name'], self.test_cg.name)
        self.assertEqual(self.test_cg.grading_policy, self.points_earned)
        self.assertNotEqual(self.test_cg.grading_policy, self.trials_count)

        self.assertRedirects(response, reverse('module:group-detail', kwargs={'group_slug': self.test_cg.slug}))

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
        super(TestBackURLMixin, self).setUp()
        self.back_url = '/test_back_url/'

    def test_collection_edit_back_url(self):
        """Test back_url param is added into context in collection change view."""
        url = (
            reverse('module:collection-change', kwargs={'pk': self.collection1.id}) +
            '?back_url={}'.format(self.back_url)
        )
        change_response = self.client.get(url)
        self.assertIn('back_url', change_response.context)
        self.assertEqual(change_response.context['back_url'], self.back_url)

    def test_collection_detail_back_url(self):
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
        super(TestCourseViews, self).setUp()

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
        response = self.client.post(url, data=data)
        new_course = Course.objects.exclude(id=self.course.id).get(**data)
        self.assertNotEqual(Course.objects.count(), courses_count)
        self.assertRedirects(response, reverse('module:course-detail', kwargs={'course_slug': new_course.slug}))

    def test_update_course(self):
        url = reverse('module:course-change', kwargs={'course_slug': self.course.slug})
        data = {
            'name': 'Some new course 111',
            'description': 'bla bla bla 1111',
            'owner': self.user.id
        }
        courses_count = Course.objects.count()
        response = self.client.post(url, data=data)
        self.assertEqual(Course.objects.count(), courses_count)
        course = Course.objects.get(id=self.course.id)
        self.assertRedirects(response, reverse('module:course-detail', kwargs={'course_slug': course.slug}))
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
        col_id = self.collection1.id
        expected_url = reverse('module:collection-detail', kwargs={'pk': col_id}) + '?back_url=None'
        url = reverse('module:collection-sync', kwargs={'pk': col_id})
        response = self.client.get(url)
        mock_delay.assert_called_once_with(
            collection_id=str(col_id),
            created_at=Collection.objects.get(pk=col_id).updated_at
        )
        self.assertRedirects(response, expected_url)

    @patch('module.tasks.sync_collection_engines.delay')
    @patch('module.tasks.sync_collection_engines.apply_async')
    @patch('module.views.get_available_courses')
    def test_immediate_synchronization_incorrect_pk(
        self, mock_get_available_courses, mock_apply_async, mock_delay
    ):
        col_id = 345
        url = reverse('module:collection-sync', kwargs={'pk': col_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
