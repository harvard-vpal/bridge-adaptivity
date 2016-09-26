import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings

auth = HTTPBasicAuth(settings.TUTORGEN_USER,settings.TUTORGEN_PASS)

class Transaction:
    def __init__(self, attempt):
        # datestamp has format "13 September 2016"
        datestamp = "{day} {month} {year}".format(
            day = attempt.timestamp.day,
            month = attempt.timestamp.strftime('%B'),
            year = attempt.timestamp.year,
        )
        # timestamp has format 21:01
        timestamp = "{hour}:{minute}".format(
            hour = attempt.timestamp.hour,
            minute = attempt.timestamp.minute,
        )
        # determine correctness
        problem_result = 'correct' if attempt.points==attempt.max_points else 'incorrect'
        # construct the post request data
        json = {
            'course_id': settings.TUTORGEN_COURSE_ID,
            'datestamp': datestamp,
            'problem_id': attempt.activity.pk,
            'problem_result': problem_result,
            'learner_id': attempt.user.pk,
            'timestamp': timestamp,
        }
        print "sending transaction to tutorgen: {}".format(json)
        # send the post request
        r = requests.post("{}/transaction".format(settings.TUTORGEN_URL_BASE),
            auth=auth,
            json=json,
        )
        self.response = r.json()

    def success(self):
        '''
        Returns True if the transaction was successfully created for tutorgen
        '''
        if self.response['status'] == 201:
            return True


class Activity:
    def __init__(self, user_module):
        '''
        Get a recommendation for new activity
        methods used for getting activity_id and whether student is done with module
        '''
        params = {
            'learner_id': user_module.user.pk,
            'section': user_module.module.pk,
            # 'subsection': subsection,
            # 'unit': unit
        }
        r = requests.get(
            "{}/activity".format(settings.TUTORGEN_URL_BASE),
            auth=auth,
            params=params,
        )
        self.response = r.json()
        print "requested activity from tutorgen, sent: {}, recieved: {}".format(params,self.response)
        self.activity_info = self.response['_embedded']['item'][0]


    def get_activity_id(self):
        return self.activity_info['next_activity']

    def level_up(self):
        return self.activity_info['level_up']


        # # grab activity id from api response
        # level_up = False
        # for record in self.response['_embedded']['item']:
        #     if record['learner_id'] == user.pk:
        #         return level_up = record['level_up']




