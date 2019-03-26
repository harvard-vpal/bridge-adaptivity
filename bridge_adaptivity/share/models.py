from django.db import models

from bridge_lti.models import BridgeUser


class Resource(models.Model):
    """
    Resource that Bridge user share with other Bridge users
    """
    owner = models.ForeignKey(BridgeUser, on_delete=models.CASCADE)


class ResourcePermissionToUser(models.Model):
    """
    Permission to Resource for LTI user
    """
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    user = models.ForeignKey(BridgeUser, on_delete=models.CASCADE)
