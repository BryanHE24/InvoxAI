# backend/services/s3_service.py
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
import os
import uuid
import logging

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self, app_config):
        self.config = app_config
        self.aws_access_key_id = self.config.get('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = self.config.get('AWS_SECRET_ACCESS_KEY')
        self.region_name = self.config.get('AWS_REGION')
        self.bucket_name = self.config.get('S3_BUCKET_NAME')

        if not all([self.region_name, self.bucket_name]):
            logger.error("S3Service: AWS_REGION or S3_BUCKET_NAME not configured.")
            raise ValueError("S3Service: AWS_REGION or S3_BUCKET_NAME not configured.")

        if self.aws_access_key_id and self.aws_secret_access_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name
            )
            logger.info("S3Service initialized with explicit credentials.")
        else:
            self.s3_client = boto3.client('s3', region_name=self.region_name)
            logger.info("S3Service initialized (credentials will be sourced by boto3).")

    def upload_file_obj(self, file_obj, object_name=None, folder='invoices'):
        if not self.bucket_name:
            logger.error("S3 bucket name not configured for upload.")
            return None

        if object_name is None:
            object_name = file_obj.filename
        
        _, file_extension = os.path.splitext(object_name)
        s3_object_key = f"{folder.strip('/')}/{uuid.uuid4()}{file_extension}"

        try:
            file_obj.seek(0)
            
            content_type = file_obj.content_type
            if not content_type:
                ext_lower = file_extension.lower()
                if ext_lower in ['.png', '.jpg', '.jpeg', '.gif']:
                    content_type = f'image/{ext_lower[1:]}'
                elif ext_lower == '.pdf':
                    content_type = 'application/pdf'
                else:
                    content_type = 'application/octet-stream'
            logger.debug(f"Uploading to S3 with ContentType: {content_type}")

            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_object_key,
                ExtraArgs={'ContentType': content_type}
            )
            logger.info(f"File {object_name} uploaded to {self.bucket_name}/{s3_object_key}")
            return s3_object_key
        except (NoCredentialsError, PartialCredentialsError) as e:
            logger.error(f"S3 Upload Credentials Error: {e}")
            return None
        except ClientError as e:
            logger.error(f"S3 ClientError during upload to {s3_object_key}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during S3 upload: {e}", exc_info=True)
            return None

    def get_presigned_url(self, object_key, expiration=3600, bucket_name=None):
        target_bucket = bucket_name if bucket_name else self.bucket_name
        if not target_bucket:
            logger.error("S3 bucket name not available for presigned URL.")
            return None
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': target_bucket, 'Key': object_key},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"S3 ClientError generating presigned URL for {target_bucket}/{object_key}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {e}", exc_info=True)
            return None
      
    def delete_file_obj(self, object_key, bucket_name=None):
        """
        Deletes an object from an S3 bucket.
        :param object_key: The key of the object to delete.
        :param bucket_name: Optional. The name of the bucket. Uses configured bucket_name if None.
        :return: True if deletion was successful or object didn't exist, False on error.
        """
        target_bucket = bucket_name if bucket_name else self.bucket_name
        if not target_bucket:
            logger.error("S3 delete: Bucket name not configured or provided.")
            return False
        
        try:
            logger.info(f"Attempting to delete S3 object: {target_bucket}/{object_key}")
            self.s3_client.delete_object(Bucket=target_bucket, Key=object_key)
            logger.info(f"S3 object deleted (or did not exist): {target_bucket}/{object_key}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"S3 delete: Object {target_bucket}/{object_key} not found, considered success.")
                return True # If it doesn't exist, it's effectively "deleted"
            logger.error(f"S3 ClientError during delete for {target_bucket}/{object_key}: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error during S3 delete for {target_bucket}/{object_key}: {e}", exc_info=True)
            return False