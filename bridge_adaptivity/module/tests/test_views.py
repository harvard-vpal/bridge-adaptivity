from django.test import TestCase
from django.urls.base import reverse
from mock import patch

from module.models import BridgeUser, Collection, CollectionGroup, Engine


class BridgeTestCase(TestCase):
    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        self.user = BridgeUser.objects.create_user(
            username='test',
            password='test',
            email='test@me.com'
        )
        self.client.login(username='test', password='test')
        self.collection1 = Collection.objects.create(name='col1', owner=self.user)
        self.collection2 = Collection.objects.create(name='col2', owner=self.user)
        self.collection3 = Collection.objects.create(name='col3', owner=self.user)
        self.engine = Engine.objects.create(engine='engine_mock')
        self.test_cg = CollectionGroup.objects.create(
            name='TestColGroup',
            owner=self.user,
            engine=self.engine
        )
        self.test_cg.collections.add(self.collection1)
        self.test_cg.collections.add(self.collection3)


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


class TestCollectionGroupTest(BridgeTestCase):
    def test_create_cg_page_works(self):
        """Test that CollectionGroup page works correctly contain valid context and response code is 200."""
        url = reverse('module:group-add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        groups_count = CollectionGroup.objects.count()
        response = self.client.post(url, data={
            'name': "CG1",
            "collections": [self.collection1.id, self.collection2.id],
            'engine': self.engine.id,
            'owner': self.user.id
        })
        self.assertEqual(groups_count + 1, CollectionGroup.objects.count())
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
        data = {
            'name': "CG2",
            "collections": [self.collection1.id, self.collection2.id, self.collection3.id],
            'engine': self.engine.id,
            'owner': self.user.id
        }
        cnt = CollectionGroup.objects.count()
        url = reverse('module:group-change', kwargs={'pk': self.test_cg.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('module:group-detail', kwargs={'pk': self.test_cg.id}))
        self.assertEqual(cnt, CollectionGroup.objects.count())
        test_g = CollectionGroup.objects.get(id=self.test_cg.id)
        self.assertNotEqual(test_g.name, self.test_cg.name)
        self.assertNotEqual(test_g.collections.all(), self.test_cg.collections.all())
