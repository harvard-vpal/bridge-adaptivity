import importlib
import logging

from django.conf import settings

log = logging.getLogger(__name__)

ENGINE_MOCK_MODULE = 'module.engines.engine_mock'  # By default Mock Engine is used
ENGINE_MOCK_DRIVER = 'EngineMock'
ENGINE_MODULE = getattr(settings, 'ENGINE_MODULE', ENGINE_MOCK_MODULE)
ENGINE_DRIVER = getattr(settings, 'ENGINE_DRIVER', ENGINE_MOCK_DRIVER)
ENGINE_SETTINGS = getattr(settings, 'ENGINE_SETTINGS', {})

engine = None

try:
    engine = importlib.import_module(ENGINE_MODULE)
except ImportError:
    log.exception("Engine Driver {} cannot be imported, default Engine Mock will be used.".format(ENGINE_DRIVER))
    engine = importlib.import_module(ENGINE_MOCK_MODULE)

ENGINE = getattr(engine, ENGINE_DRIVER)(**ENGINE_SETTINGS)
