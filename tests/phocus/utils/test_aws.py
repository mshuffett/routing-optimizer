import os
import pytest

from phocus.utils.aws import S3Utility
from phocus.utils.constants import DATA_PATH

###############################################################
# global config vars
# change when transferring AWS accounts
###############################################################
_DEFAULT_S3_BUCKET_NAME = 'qcclient-phocus-tech'
_DEFAULT_S3_DATA_FOLDER = 'optimizer-data'
_DEFAULT_DATA_FILE = 'long_island_locs.csv'

s3_utility = None
try:
    s3_utility = S3Utility(bucket_name=_DEFAULT_S3_BUCKET_NAME)
except Exception:
    pass


@pytest.mark.skipif(s3_utility is None, reason='S3Utility could not be created, likely because key was not given.')
def test_s3_utility():
    # compute relevant paths
    _DEFAULT_DATA_LOC = os.path.join(DATA_PATH, _DEFAULT_DATA_FILE)
    _DEFAULT_S3_DATA_KEY = '{0}/{1}'.format(_DEFAULT_S3_DATA_FOLDER, _DEFAULT_DATA_FILE)

    # test list
    print('Testing list...')
    listed_keys = s3_utility.list('')
    print('Listed keys: {0}'.format(listed_keys))

    # test write
    print('Testing write...')
    s3_utility.write(_DEFAULT_DATA_LOC, _DEFAULT_S3_DATA_KEY)

    # test read
    print('Testing read...')
    tmp_loc = s3_utility.read(_DEFAULT_S3_DATA_KEY)
    os.system('head {0}'.format(tmp_loc))

    # test delete
    print('Testing delete...')
    s3_utility.delete(_DEFAULT_S3_DATA_KEY)
