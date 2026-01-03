"""Tests for src/common/aws.py - AWS client caching."""

import pytest
from unittest.mock import patch, MagicMock

from src.common.aws import (
    get_bedrock_runtime,
    get_transcribe_client,
    get_comprehend_medical_client,
    get_s3_client,
    DEFAULT_REGION,
)


class TestAWSClientCaching:
    """Tests for AWS client factory caching."""

    def setup_method(self):
        """Clear LRU cache before each test."""
        get_bedrock_runtime.cache_clear()
        get_transcribe_client.cache_clear()
        get_comprehend_medical_client.cache_clear()
        get_s3_client.cache_clear()

    @patch("src.common.aws.boto3.client")
    def test_get_bedrock_runtime_creates_client(self, mock_boto3_client):
        """get_bedrock_runtime should create a Bedrock client."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        client = get_bedrock_runtime()
        
        mock_boto3_client.assert_called_once_with(
            service_name="bedrock-runtime",
            region_name=DEFAULT_REGION
        )
        assert client == mock_client

    @patch("src.common.aws.boto3.client")
    def test_get_bedrock_runtime_uses_provided_region(self, mock_boto3_client):
        """get_bedrock_runtime should use provided region."""
        get_bedrock_runtime.cache_clear()
        mock_boto3_client.return_value = MagicMock()
        
        get_bedrock_runtime(region_name="us-east-1")
        
        mock_boto3_client.assert_called_once_with(
            service_name="bedrock-runtime",
            region_name="us-east-1"
        )

    @patch("src.common.aws.boto3.client")
    def test_get_bedrock_runtime_caches_client(self, mock_boto3_client):
        """get_bedrock_runtime should cache the client (same region)."""
        mock_boto3_client.return_value = MagicMock()
        
        client1 = get_bedrock_runtime()
        client2 = get_bedrock_runtime()
        
        # Should only call boto3.client once due to caching
        assert mock_boto3_client.call_count == 1
        assert client1 is client2

    @patch("src.common.aws.boto3.client")
    def test_get_transcribe_client_creates_client(self, mock_boto3_client):
        """get_transcribe_client should create a Transcribe client."""
        get_transcribe_client.cache_clear()
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        client = get_transcribe_client()
        
        mock_boto3_client.assert_called_once_with(
            service_name="transcribe",
            region_name=DEFAULT_REGION
        )
        assert client == mock_client

    @patch("src.common.aws.boto3.client")
    def test_get_comprehend_medical_client_creates_client(self, mock_boto3_client):
        """get_comprehend_medical_client should create a Comprehend Medical client."""
        get_comprehend_medical_client.cache_clear()
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        client = get_comprehend_medical_client()
        
        mock_boto3_client.assert_called_once_with(
            service_name="comprehendmedical",
            region_name=DEFAULT_REGION
        )
        assert client == mock_client

    @patch("src.common.aws.boto3.client")
    def test_get_s3_client_creates_client(self, mock_boto3_client):
        """get_s3_client should create an S3 client."""
        get_s3_client.cache_clear()
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        client = get_s3_client()
        
        mock_boto3_client.assert_called_once_with(
            service_name="s3",
            region_name=DEFAULT_REGION
        )
        assert client == mock_client

    def test_default_region_is_ap_southeast_2(self):
        """DEFAULT_REGION should be ap-southeast-2 (Sydney)."""
        assert DEFAULT_REGION == "ap-southeast-2"

    @patch("src.common.aws.boto3.client")
    def test_different_regions_create_different_caches(self, mock_boto3_client):
        """Different regions should create separate cached clients."""
        get_bedrock_runtime.cache_clear()
        mock_boto3_client.return_value = MagicMock()
        
        client1 = get_bedrock_runtime(region_name="ap-southeast-2")
        client2 = get_bedrock_runtime(region_name="us-east-1")
        
        # Should call boto3.client twice (different regions = different cache entries)
        assert mock_boto3_client.call_count == 2
        
        # Verify each call had correct region
        calls = mock_boto3_client.call_args_list
        assert calls[0][1]["region_name"] == "ap-southeast-2"
        assert calls[1][1]["region_name"] == "us-east-1"


class TestAWSClientUsage:
    """Tests for expected usage patterns of AWS clients."""

    def test_all_clients_have_lru_cache_decorator(self):
        """All AWS client factories should have LRU cache."""
        # Check that the functions have cache_clear method (indicates LRU cache)
        assert hasattr(get_bedrock_runtime, "cache_clear")
        assert hasattr(get_transcribe_client, "cache_clear")
        assert hasattr(get_comprehend_medical_client, "cache_clear")
        assert hasattr(get_s3_client, "cache_clear")

    @patch("src.common.aws.boto3.client")
    def test_multiple_client_types_can_coexist(self, mock_boto3_client):
        """Different client types should be cached separately."""
        # This is a sanity check that different services maintain separate caches
        get_bedrock_runtime.cache_clear()
        get_s3_client.cache_clear()
        
        mock_bedrock = MagicMock(name="bedrock")
        mock_s3 = MagicMock(name="s3")
        
        def mock_client_factory(service_name, region_name):
            if service_name == "bedrock-runtime":
                return mock_bedrock
            elif service_name == "s3":
                return mock_s3
            return MagicMock()
        
        mock_boto3_client.side_effect = mock_client_factory
        
        bedrock = get_bedrock_runtime()
        s3 = get_s3_client()
        
        assert bedrock == mock_bedrock
        assert s3 == mock_s3
