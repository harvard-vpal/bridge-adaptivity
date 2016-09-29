from django.conf import settings
import module.models


class Transaction:
    def __init__(self, attempt):
        '''
        Initialization of this object "sends a transaction"
        '''
        pass

    def success(self):
        '''
        Returns True if the transaction was successfully created for tutorgen
        '''
        return True


class Activity:
    '''
    Get a recommendation for new activity
    methods used for getting activity_id and whether student is done with module
    '''
    def __init__(self, user_module):
        '''
        initialize with a module.user_module
        get a random activity from the remaining questions left in the module
        '''
        previous_activity_ids = list(user_module.sequenceitem_set.values_list('activity',flat=True))
        self.activity = (module.models.Activity.objects
            .filter(module=user_module.module)
            .exclude(pk__in=previous_activity_ids)
            .first()
        )

    def get_activity_id(self):
        return self.activity.pk

    def level_up(self):
        if not self.activity:
            return True
        else:
            return False
