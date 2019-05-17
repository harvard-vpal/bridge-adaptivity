from channels.testing import ChannelsLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from mock import patch
from module.tests.test_views import BridgeTestCase
from module.models import Activity, Sequence, SequenceItem, BridgeUser
from bridge_lti.models import LtiContentSource, LtiUser, OutcomeService, LtiLmsPlatform
from django.contrib.auth.models import Group
from django.urls.base import reverse
# from selenium_testcase.testcases import SeleniumLiveTestCase
# from django_selenium.testcases import SeleniumTestCase

from selenium import webdriver
from selenium.webdriver.common.keys import Keys

class ChatTests(ChannelsLiveServerTestCase, BridgeTestCase):
    serve_static = True  # emulate StaticLiveServerTestCase

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            # NOTE: Requires "chromedriver" binary to be installed in $PATH
            # cls.driver = webdriver.Remote('chromedriver:4444', DesiredCapabilities.CHROME)
            options = webdriver.ChromeOptions()
            options.add_argument('--disable-extensions')
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            cls.driver = webdriver.Chrome('/chromedriver/chromedriver', chrome_options=options)
        except:
            super().tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        cls.user2 = BridgeUser.objects.create_user(
            username='test2',
            password='test2',
            email='tes2t@me.com'
        )

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        super().setUp()

        # self.user2 = BridgeUser.objects.create_user(
        #     username='test2',
        #     password='test2',
        #     email='tes2t@me.com'
        # )
        self.lti_user = LtiUser(
            user_id='test',
            course_id='course_id',
            email='test@me.com',
            lti_lms_platform=self.lti_lms_platform,
            bridge_user=self.user,
        )
        self.outcome_servise = OutcomeService.objects.create(
            lis_outcome_service_url='lis_outcome_service_url',
            lms_lti_connection=self.lti_lms_platform,
        )
        # self.group = Group(name='test group')
        self.lti_content_source = LtiContentSource.objects.create(
            name="test",
            provider_key='provider_key',
            provider_secret='provider_secret',
            is_active=True,
            # available_in_groups__id=self.group.id
        )
        self.lti_content_source.available_in_groups.get_or_create(name='test group')
        self.first_activity = Activity.objects.create(
            name="first_activity",
            collection=self.collection1,
            difficulty=0.5,
            lti_content_source=self.lti_content_source,
            repetition=1
        )
        self.second_activity = Activity.objects.create(
            name="second activity",
            collection=self.collection1,
            difficulty=0.5,
            lti_content_source=self.lti_content_source,
            repetition=1
        )
        self.third_activity = Activity.objects.create(
            name="third_activity",
            collection=self.collection3,
            difficulty=0.5,
            lti_content_source=self.lti_content_source,
            repetition=1
        )
        self.fourth_activity = Activity.objects.create(
            name="fourth activity",
            collection=self.collection3,
            difficulty=0.5,
            lti_content_source=self.lti_content_source,
            repetition=1
        )
        self.sequence = Sequence(
            lti_user=self.lti_user,
            collection_order=self.collection_order1,
            completed=False,
            suffix='test'
        )
        self.sequence_item_one = SequenceItem(
            sequence=self.sequence,
            activity=self.first_activity,
            position=1
        )
        self.sequence_item_one = SequenceItem(
            sequence=self.sequence,
            activity=self.second_activity,
            position=2
        )
        self.driver.get(self.live_server_url)
        username = self.driver.find_element_by_name('username')
        username.clear()
        username.send_keys("test2")
        password = self.driver.find_element_by_name('password')
        password.clear()
        password.send_keys("test2")
        submit = self.driver.find_element_by_xpath("//input[@type='submit']")
        submit.click()


    def test_next_button_must_be_disable(self):
        demo_url = f"{self.live_server_url}{reverse('module:demo', kwargs={'collection_order_slug': self.collection1.slug})}"
        self.driver.get(demo_url)
        next_button = self.driver.find_element_by_css_selector(".next-button-link")








