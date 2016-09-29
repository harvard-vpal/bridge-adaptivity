from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
import logging
# using dce_lti_py instad of ims_lti_py for grade passback
from dce_lti_py import OutcomeRequest

from module.models import UserModule, Module
from lti.models import LtiParameters

logger = logging.getLogger(__name__)


@login_required()
@require_http_methods(['POST'])
def launch(request):
    '''
    Standard LTI launch
    Expects an additional POST param, "module", to know module context; set this in "custom parameters" section
    Saves or updates LTI parameters in db
    Redirects to a user_module-specific launch view
        '''
    if 'custom_module' not in request.POST:
        raise Http404('custom parameter "module" not specified in custom LTI parameters')
    module_id = int(request.POST['custom_module'])
    module = get_object_or_404(Module,pk=module_id)

    # create new usermodule object if doesnt exist
    user_module, created = UserModule.objects.get_or_create(
        user = request.user,
        module = module,
    )

    # save or update user LTI parameters in db
    lti_parameters, created = LtiParameters.objects.get_or_create(user_module=user_module)

    for parameter_name in lti_parameters.parameter_list:
        setattr(lti_parameters, parameter_name, request.POST.get(parameter_name,''))
    
    # save raw post request
    lti_parameters.data = json.dumps(dict(request.POST))
    lti_parameters.save()

    return redirect('module:launch', user_module_id=user_module.pk)


