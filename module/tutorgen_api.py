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

        # send the post request
        r = requests.post("{}/transaction".format(settings.TUTORGEN_URL_BASE),
            auth=auth,
            json=json,
        )
        self.response = r.json()
        print "TUTORGEN POST TRANSACTION: sent: {}".format(json)

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
        print "TUTORGEN: GET ACTIVITY, sent: {}, received: {}".format(params,self.response)
        result = self.response['_embedded']['item']
        if len(result)==1:
            self.activity_info = result[0]
        elif len(result)==0:
            print 
            self.activity_info = None
        elif len(result)>1:
            print "TUTORGEN: ERROR more than one item returned in get activity request"

    def get_activity_id(self):
        if self.activity_info:
            return self.activity_info['next_activity']
        else:
            return None

    def level_up(self):
        if self.activity_info:
            return self.activity_info['level_up']=='true'
        else:
            return False


