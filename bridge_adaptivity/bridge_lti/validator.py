"""
From the openEDX app -> lti_provider
Subclass of oauthlib's RequestValidator that checks an OAuth signature.
"""
import logging

from django.conf import settings
from django.core.cache import cache
from oauthlib.oauth1 import SignatureOnlyEndpoint
from oauthlib.oauth1 import RequestValidator

from bridge_lti.models import LtiProvider

log = logging.getLogger(__name__)


class SignatureValidator(RequestValidator):
    """
    Helper class that verifies the OAuth signature on a request.

    The pattern required by the oauthlib library mandates that subclasses of
    RequestValidator contain instance methods that can be called back into in
    order to fetch the consumer secret or to check that fields conform to
    application-specific requirements.
    """

    def __init__(self):
        super(SignatureValidator, self).__init__()
        self.endpoint = SignatureOnlyEndpoint(self)
        self.lti_consumer = None
        self.cache = cache

    # The OAuth signature uses the endpoint URL as part of the request to be
    # hashed. By default, the oauthlib library rejects any URLs that do not
    # use HTTPS. We turn this behavior off in order to allow edX to run without
    # SSL in development mode. When the platform is deployed and running with
    # SSL enabled, the URL passed to the signature verifier must start with
    # 'https', otherwise the message signature would not match the one generated
    # on the platform.
    @property
    def enforce_ssl(self):
        try:
            ssl = settings.LTI_SSL
        except AttributeError:
            ssl = True
        return ssl

    def validate_timestamp_and_nonce(self, client_key, timestamp, nonce, request):
        """
        Verify that the request is not too old (according to the timestamp), and
        that the nonce value has not been used already within the period of time
        in which the timestamp marks a request as valid. This method signature
        is required by the oauthlib library.

        :return: True if the OAuth nonce and timestamp are valid, False if they
        are not.
        """
        msg = "LTI request's {} is not valid."

        log.debug('Timestamp validating is started.')
        ts = int(timestamp)
        ts_key = '{}_ts'.format(client_key)
        cache_ts = self.cache.get(ts_key, ts)
        log.error("cache ts: {}; ts: {}; valid: {}".format(type(cache_ts), type(ts), cache_ts < ts))
        if cache_ts > ts:
            log.debug(msg.format('timestamp'))
            return False
        self.cache.set(ts_key, ts, 10)
        log.debug('Timestamp is valid.')

        log.debug('Nonce validating is started.')
        if self.cache.get(nonce):
            log.debug(msg.format('nonce'))
            return False
        self.cache.set(nonce, 1)
        log.debug('Nonce is valid.')
        return True

    def validate_client_key(self, client_key, request):
        """
        Ensure that the client key supplied with the LTI launch is on that has
        been generated by our platform, and that it has an associated client
        secret.

        :return: True if the key is valid, False if it is not.
        """
        try:
            self.lti_consumer = LtiProvider.objects.get(consumer_key=client_key)
        except LtiProvider.DoesNotExist:
            log.exception('Consumer with the key {} is not found.'.format(client_key))
            return False
        return True

    def get_client_secret(self, client_key, request):
        """
        Fetch the client secret from the database. This method signature is
        required by the oauthlib library.

        :return: the client secret that corresponds to the supplied key if
        present, or None if the key does not exist in the database.
        """
        log.debug('Getting client secret')
        return self.lti_consumer.consumer_secret
