# coding: utf-8
from django.forms import widgets


class PolicyChoiceWidget(widgets.ChoiceWidget):
    """This widget inherited from ChoiceWidget change templates used for policy choose."""

    checked_attribute = {'selected': True}
    template_name = 'module/widgets/select_policy.html'
    option_template_name = 'module/widgets/select_policy_option.html'
