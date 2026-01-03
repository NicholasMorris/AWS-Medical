import boto3
from functools import lru_cache
from typing import Optional

DEFAULT_REGION = "ap-southeast-2"


@lru_cache
def get_bedrock_runtime(region_name: Optional[str] = None):
    """
    Returns a cached Bedrock Runtime client.
    """
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=region_name or DEFAULT_REGION,
    )


@lru_cache
def get_transcribe_client(region_name: Optional[str] = None):
    """
    Returns a cached AWS Transcribe client.
    """
    return boto3.client(
        service_name="transcribe",
        region_name=region_name or DEFAULT_REGION,
    )


@lru_cache
def get_comprehend_medical_client(region_name: Optional[str] = None):
    """
    Returns a cached AWS Comprehend Medical client.
    """
    return boto3.client(
        service_name="comprehendmedical",
        region_name=region_name or DEFAULT_REGION,
    )

@lru_cache
def get_s3_client(region_name: Optional[str] = None):
    """
    Returns a cached AWS S3 client.
    """
    return boto3.client(
        service_name="s3",
        region_name=region_name or DEFAULT_REGION,
    )