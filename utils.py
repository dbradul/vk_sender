import csv
import functools
import itertools
import logging
from datetime import datetime

from vk_api import ApiError

from models import VkClientProxy

log_file = "./logfile.log"
log_level = logging.INFO
logging.basicConfig(
    level=log_level, filename=log_file, filemode="a+", format="%(asctime)-15s %(levelname)-8s %(message)s"
)
logger = logging.getLogger("date_parser")
logger.addHandler(logging.StreamHandler())


ERROR_RATE_LIMIT_EXCEEDED = 29
ERROR_PROFILE_IS_PRIVATE = 30
class RateLimitException(Exception):
    pass

class ProfileIsPrivateException(Exception):
    pass


# ----------------------------------------------------------------------------------------------------------------------
def from_unix_time(ts):
    return datetime.utcfromtimestamp(ts)


def repack_exc(func):
    @functools.wraps(func)
    def inner(client, *args, **kwargs):
        try:
            return func(client, *args, **kwargs)

        except ApiError as ex:
            if ex.code == ERROR_RATE_LIMIT_EXCEEDED:
                raise RateLimitException(str(ex))
            elif ex.code == ERROR_PROFILE_IS_PRIVATE:
                raise ProfileIsPrivateException(str(ex))
            else:
                raise
    return inner


def login_retrier(func):
    @functools.wraps(func)
    def inner(client: VkClientProxy, *args, **kwargs):
        try:
            result = func(client, *args, **kwargs)
            return result

        except RateLimitException as ex:
            logger.error(f'Retrying after error: {ex}')
            for account, _ in client._accounts:
                try:
                    client.direct_auth(app_id=os.getenv('VK_APP_ID'), client_secret=os.getenv('VK_APP_SECRET'))
                    result = func(client, *args, **kwargs)
                    return result
                except RateLimitException as ex:
                    logger.error(f'Failed with account {account}. Retrying after error: {ex}')
            else:
                raise RateLimitException(str(ex))
    return inner

