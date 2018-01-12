# Common for modules functions are gathering in utils module


def save_model_parameter_true_once(instance, parameter):
    if getattr(instance, parameter, None):
        filter_kwargs, update_kwargs = ({parameter: True}, {parameter: False})
        instance.__class__.objects.filter(**filter_kwargs).update(**update_kwargs)
