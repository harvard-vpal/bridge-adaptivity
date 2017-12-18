from django.test import TestCase
from django.urls.base import reverse
from module.models import BridgeUser, CollectionGroup, Collection, Engine


class TestCollectionGroupTest(TestCase):
    def setUp(self):
        self.user = BridgeUser.objects.create_user(
            username='test',
            password='test',
            email='test@me.com'
        )
        self.client.login(username='test', password='test')
        self.collection1 = Collection.objects.create(name='col1', owner=self.user)
        self.collection2 = Collection.objects.create(name='col2', owner=self.user)
        self.collection3 = Collection.objects.create(name='col3', owner=self.user)
        self.engine = Engine.objects.create(name='mock')
        self.test_cg = CollectionGroup.objects.create(
            name='TestColGroup',
            owner=self.user,
            engine=self.engine
        )
        self.test_cg.collections.add(self.collection1)
        self.test_cg.collections.add(self.collection3)


    def test_create_cg_page_works(self):
        url = reverse('module:group-add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        cnt = CollectionGroup.objects.count()
        response = self.client.post(url, data={
            'name': "CG1",
            "collections": [self.collection1.id, self.collection2.id],
            'engine': self.engine.id,
            'owner': self.user.id
        })
        self.assertEqual(cnt+1, CollectionGroup.objects.count())
        self.assertEqual(response.status_code, 302)

    def test_cg_list(self):
        url = reverse('module:group-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('groups', response.context)
        self.assertCountEqual(response.context['groups'], CollectionGroup.objects.filter(owner=self.user))

    def test_update_cg(self):
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
        # self.assertEqual(response.status_code, 200)
        self.assertEqual(cnt, CollectionGroup.objects.count())
        test_g = CollectionGroup.objects.get(id=self.test_cg.id)
        self.assertNotEqual(test_g.name, self.test_cg.name)
        self.assertNotEqual(test_g.collections.all(), self.test_cg.collections.all())











