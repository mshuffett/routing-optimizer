import os
import boto3
import random


class AWSUtility:
    """
    Base AWS utility class to initialize keys for all subsequent AWS service classes
    """

    def __init__(self):
        # initialize keys, exit if not found
        environ = dict(os.environ)
        if 'AWS_ACCESS_KEY_ID' not in environ or 'AWS_SECRET_ACCESS_KEY' not in environ:
            raise Exception('Please specify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY!')
        self.aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID']
        self.aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']


class S3Utility(AWSUtility):
    """
    S3 utility class: currently supports list, read, write, delete
    """

    def __init__(self, bucket_name, tmp_dir='/tmp'):
        super().__init__()
        self.s3_client = boto3.client('s3')

        # name of bucket to read and write data from
        self.bucket_name = bucket_name

        # name of tmp dir on node to download data
        self.tmp_dir = tmp_dir

    def list(self, prefix=''):
        """
        List all objects in the relevant bucket
        """
        res = self.s3_client.list_objects(Bucket=self.bucket_name, Prefix=prefix)['Contents']

        # only get the key names and remove directories
        res = [x['Key'] for x in res]
        res = list(filter(lambda x: x[-1] != '/', res))

        return res

    def read(self, src_key):
        """
        Read a S3 object to the tmp_dir
        """
        # set up the download to tmp directory, removing any
        # possible collision
        dest_name = 'qc_' + str(random.randint(99999999, 999999999))
        dest_loc = os.path.join(self.tmp_dir, dest_name)
        os.system('rm -f {0}'.format(dest_loc))

        # download to tmp dir
        print('[S3] Reading from {0}...'.format(src_key))
        self.s3_client.download_file(self.bucket_name, src_key, dest_loc)

        # return path to file for later use
        print('Downloading: {0}'.format(dest_loc))
        return dest_loc

    def write(self, src_loc, dest_key):
        """
        Write a file to S3
        """
        # upload
        print('[S3] Writing to {0}...'.format(dest_key))
        self.s3_client.upload_file(src_loc, self.bucket_name, dest_key)

    def delete(self, key):
        """
        Delete a file on S3
        """
        # delete
        print('[S3] Deleting {0}...'.format(key))
        self.s3_client.delete_object(
            Bucket=self.bucket_name,
            Key=key
        )
