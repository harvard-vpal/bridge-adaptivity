from django.db import models
# from django.contrib.auth.models import User
from module.models import Module, UserModule


class LtiParameters(models.Model):
    '''
    Used to store outcome service url for a particular user and module
    Enables asynchronous or API-triggered grade passback
    '''

    user_module = models.OneToOneField(UserModule)
    timestamp_last_launch = models.DateTimeField(null=True,auto_now=True)

    # save all raw POST parameters
    data = models.TextField(default='')

    # explicitly stored LTI parameters
    lis_outcome_service_url = models.CharField(max_length=300,default='')
    lis_result_sourcedid = models.CharField(max_length=300,default='')
    oauth_consumer_key = models.CharField(max_length=300,default='')
    user_id = models.CharField(max_length=300,default='') # lti user id
    lis_person_sourcedid = models.CharField(max_length=300,default='') #edx username
    roles = models.CharField(max_length=300,default='') # roles

    parameter_list = [
        'lis_outcome_service_url',
        'lis_result_sourcedid',
        'oauth_consumer_key',
        'user_id',
        'lis_person_sourcedid',
        'roles',
    ]

    class Meta:
        verbose_name = 'LTI Parameters'
        verbose_name_plural = 'LTI Parameters'

