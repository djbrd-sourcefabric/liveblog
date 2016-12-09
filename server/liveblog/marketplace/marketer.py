import logging
import requests
from flask import abort, Blueprint, request
from flask_cors import CORS
from liveblog.syndication.utils import api_response, api_error
from liveblog.syndication.exceptions import APIConnectionError
from apps.auth import SuperdeskTokenAuth
from settings import MARKETPLACE_APP_URL
from requests.exceptions import RequestException
from requests.packages.urllib3.exceptions import MaxRetryError
from urllib.parse import urljoin


logger = logging.getLogger('superdesk')
marketers_blueprint = Blueprint('marketers', __name__)
CORS(marketers_blueprint)


# For retrieving a list of marketers from the market place app
@marketers_blueprint.route('/api/marketplace/marketers', methods=['GET'])
def marketers():
    # Use marketplace app url to retrieve marketers
    try:
        response = _send_marketplace_api_request(MARKETPLACE_APP_URL, 'marketers')
    except APIConnectionError as e:
        return api_response(str(e), 500)

    if response.status_code == 200:
        return api_response(response.content, response.status_code, json_dumps=False)
    else:
        return api_error('Unable to get marketers.', response.status_code)


# For retrieving list of blogs available in marketplace from given source
@marketers_blueprint.route('/api/marketplace/marketers/<marketer_id>/blogs', methods=['GET'])
def marketer_blogs(marketer_id):
    # Use marketplace app url to retrieve marketer by id
    uri = 'marketers/{}'.format(marketer_id)
    try:
        response = _send_marketplace_api_request(MARKETPLACE_APP_URL, uri)
    except APIConnectionError as e:
        return api_response(str(e), 500)

    if response.status_code != 200:
        return api_error('Unable to get marketer.', response.status_code)

    # Use marketer url to call /marketplace/blogs
    url = response.content['url']
    try:
        response = _send_marketplace_api_request(url, 'marketplace/blogs')
    except APIConnectionError as e:
        return api_response(str(e), 500)

    if response.status_code == 200:
        return api_response(response.content, response.status_code, json_dumps=False)
    else:
        return api_error('Unable to get blogs of marketers.', response.status_code)


def _send_marketplace_api_request(url, uri, timeout=5):
    method = 'GET'
    if not url.endswith('/'):
        url = '{}/'.format(url)

    url = urljoin(url, uri)

    logger.info('API {} request to {}'.format(method, url))
    try:
        response = requests.request(method, url, headers={
            'Content-Type': 'application/json'
        }, params=None, data=None, timeout=timeout)
    except (ConnectionError, RequestException, MaxRetryError):
        raise APIConnectionError('Unable to connect to api_url "{}".'.format(url))

    logger.warning('API {} request to {} - response: {} {}'.format(
        'GET', url, response.status_code, response.content
    ))

    return response.json()


def _producers_blueprint_auth():
    auth = SuperdeskTokenAuth()
    authorized = auth.authorized(allowed_roles=[], resource='marketers', method='GET')
    if not authorized:
        return abort(401, 'Authorization failed.')


marketers_blueprint.before_request(_producers_blueprint_auth)