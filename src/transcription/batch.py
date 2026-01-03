import boto3
import json
import time
import os
from src.common.aws import (
    get_s3_client,
    get_transcribe_client,
    get_comprehend_medical_client,
)
from src.common.io import save_medical_analysis_results

def medical_transcription_with_comprehend(
    audio_file_uri,
    output_bucket_name,
    job_name_prefix="medical-transcription",
    specialty="PRIMARYCARE",
    transcription_type="CONVERSATION",
    max_speakers=2,
    show_alternatives=False,
    max_alternatives=2,
    region_name="ap-southeast-2"
):
    """
    Perform medical transcription with speaker diarization and analyze with Comprehend Medical
    
    Args:
        audio_file_uri (str): S3 URI of the .m4a file (e.g., "s3://bucket/path/file.m4a")
        output_bucket_name (str): S3 bucket name for transcription output
        job_name_prefix (str): Prefix for the transcription job name
        specialty (str): Medical specialty - "PRIMARYCARE" (only option currently)
        transcription_type (str): "CONVERSATION" or "DICTATION"
        max_speakers (int): Maximum number of speakers to identify
        show_alternatives (bool): Whether to show alternative transcriptions
        max_alternatives (int): Number of alternatives (only used if show_alternatives=True)
        region_name (str): AWS region
    
    Returns:
        dict: Combined results from transcription and Comprehend Medical analysis
    """
    
    # Initialize AWS clients
    transcribe = get_transcribe_client()
    comprehend_medical = get_comprehend_medical_client()
    s3 = get_s3_client(region_name)
    
    # Generate unique job name
    job_name = f"{job_name_prefix}-{int(time.time())}"
    
    print(f"Starting medical transcription job: {job_name}")
    print(f"Processing .m4a file: {audio_file_uri}")
    
    # Build settings dictionary based on parameters
    settings = {
        'ShowSpeakerLabels': True,  # Enable speaker diarization
        'MaxSpeakerLabels': max_speakers
    }
    
    # Only add alternatives settings if ShowAlternatives is True
    if show_alternatives:
        settings['ShowAlternatives'] = True
        settings['MaxAlternatives'] = max_alternatives
    
    print(f"Transcription settings: {settings}")
    
    # Start medical transcription job with speaker diarization
    transcribe.start_medical_transcription_job(
        MedicalTranscriptionJobName=job_name,
        Media={
            'MediaFileUri': audio_file_uri
        },
        OutputBucketName=output_bucket_name,
        OutputKey='transcription-output/',
        LanguageCode='en-US',
        Specialty=specialty,
        Type=transcription_type,
        Settings=settings
    )
    
    # Wait for transcription to complete
    print("Waiting for transcription to complete...")
    while True:
        status = transcribe.get_medical_transcription_job(
            MedicalTranscriptionJobName=job_name
        )
        
        job_status = status['MedicalTranscriptionJob']['TranscriptionJobStatus']
        print(f"Transcription status: {job_status}")
        
        if job_status in ['COMPLETED', 'FAILED']:
            break

        time.sleep(10)  # Check every 10 seconds

    if job_status == 'FAILED':
        failure_reason = status['MedicalTranscriptionJob'].get('FailureReason', 'Unknown error')
        raise Exception(f"Transcription job failed: {failure_reason}")
    
    # Get transcription results
    transcript_uri = status['MedicalTranscriptionJob']['Transcript']['TranscriptFileUri']
    print(f"Transcription completed. Results at: {transcript_uri}")
    
    transcript_uri = status['MedicalTranscriptionJob']['Transcript']['TranscriptFileUri']
    print(f"Transcription completed. Results at: {transcript_uri}")
    
    # Parse the S3 URI to get bucket and key
    # URI format: https://s3.region.amazonaws.com/bucket/key
    # or s3://bucket/key
    if transcript_uri.startswith('https://'):
        # Parse HTTPS URL
        # Example: https://s3.ap-southeast-2.amazonaws.com/bucket/transcription-output/medical/job.json
        parts = transcript_uri.replace('https://', '').split('/')
        if parts[0].startswith('s3.'):
            # Format: s3.region.amazonaws.com/bucket/key
            bucket_name = parts[1]
            s3_key = '/'.join(parts[2:])
        else:
            # Format: bucket.s3.region.amazonaws.com/key
            bucket_name = parts[0].split('.')[0]
            s3_key = '/'.join(parts[1:])
    elif transcript_uri.startswith('s3://'):
        # Parse S3 URI
        uri_parts = transcript_uri.replace('s3://', '').split('/', 1)
        bucket_name = uri_parts[0]
        s3_key = uri_parts[1] if len(uri_parts) > 1 else ''
    else:
        raise Exception(f"Unsupported transcript URI format: {transcript_uri}")
    
    print(f"Downloading transcript from bucket: {bucket_name}, key: {s3_key}")
    
    # Download and parse transcription results using S3 client
    try:
        response = s3.get_object(Bucket=bucket_name, Key=s3_key)
        transcript_data = json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"Error downloading transcript: {str(e)}")
        print(f"Bucket: {bucket_name}")
        print(f"Key: {s3_key}")
        raise Exception(f"Failed to download transcript from S3: {str(e)}")
    
    # Extract transcript text and speaker information
    transcript_text = transcript_data['results']['transcripts'][0]['transcript']
    speaker_segments = []
    
    # Process speaker-labeled segments if available
    if 'speaker_labels' in transcript_data['results']:
        segments = transcript_data['results']['speaker_labels']['segments']
        items = transcript_data['results']['items']
        
        for segment in segments:
            speaker_label = segment['speaker_label']
            start_time = segment['start_time']
            end_time = segment['end_time']
            
            # Get text for this segment
            segment_items = [
                item for item in items 
                if 'start_time' in item and 
                float(start_time) <= float(item['start_time']) <= float(end_time)
            ]
            
            segment_text = ' '.join([
                item['alternatives'][0]['content'] 
                for item in segment_items 
                if item['type'] == 'pronunciation'
            ])
            
            speaker_segments.append({
                'speaker': speaker_label,
                'start_time': start_time,
                'end_time': end_time,
                'text': segment_text
            })
    
    print(f"Transcription text length: {len(transcript_text)} characters")
    print("Processing with Amazon Comprehend Medical...")
    
    # Analyze with Comprehend Medical - Detect Entities
    entities_response = comprehend_medical.detect_entities_v2(Text=transcript_text)
    
    # Analyze with Comprehend Medical - Detect PHI
    phi_response = comprehend_medical.detect_phi(Text=transcript_text)
    
    # Process speaker segments with Comprehend Medical if available
    speaker_analysis = []
    for segment in speaker_segments:
        if len(segment['text'].strip()) > 0:  # Only analyze non-empty segments
            try:
                segment_entities = comprehend_medical.detect_entities_v2(Text=segment['text'])
                segment_phi = comprehend_medical.detect_phi(Text=segment['text'])
                
                speaker_analysis.append({
                    'speaker': segment['speaker'],
                    'start_time': segment['start_time'],
                    'end_time': segment['end_time'],
                    'text': segment['text'],
                    'entities': segment_entities['Entities'],
                    'phi_entities': segment_phi['Entities']
                })
            except Exception as e:
                print(f"Error analyzing segment for {segment['speaker']}: {str(e)}")
                speaker_analysis.append({
                    'speaker': segment['speaker'],
                    'start_time': segment['start_time'],
                    'end_time': segment['end_time'],
                    'text': segment['text'],
                    'entities': [],
                    'phi_entities': [],
                    'error': str(e)
                })
    
    # Compile results
    results = {
        'transcription_job_name': job_name,
        'transcription_status': job_status,
        'audio_format': 'm4a',
        'full_transcript': transcript_text,
        'speaker_segments': speaker_segments,
        'medical_entities': {
            'entities': entities_response['Entities'],
            'pagination_token': entities_response.get('PaginationToken'),
            'model_version': entities_response.get('ModelVersion')
        },
        'phi_entities': {
            'entities': phi_response['Entities'],
            'pagination_token': phi_response.get('PaginationToken'),
            'model_version': phi_response.get('ModelVersion')
        },
        'speaker_analysis': speaker_analysis,
        'transcript_metadata': {
            'job_name': transcript_data['jobName'],
            'account_id': transcript_data['accountId'],
            'status': transcript_data['status']
        }
    }
    
    return results

def process_local_m4a_file(
    local_file_path,
    bucket_name,
    output_bucket_name=None,
    job_name_prefix="medical-transcription",
    specialty="PRIMARYCARE",
    transcription_type="CONVERSATION",
    max_speakers=2,
    show_alternatives=False,  # Default to False to avoid the error
    max_alternatives=2,
    region_name="us-east-1",
    cleanup_s3_file=False
):
    """
    Complete workflow: Upload local .m4a file and process it
    """
    
    if output_bucket_name is None:
        output_bucket_name = bucket_name
    
    try:
        # Step 1: Upload local file to S3
        print("Step 1: Uploading local .m4a file to S3...")
        s3_uri = upload_m4a_to_s3(
            local_file_path=local_file_path,
            bucket_name=bucket_name,
            region_name=region_name
        )
        
        # Step 2: Process the file
        print("\nStep 2: Starting medical transcription and analysis...")
        results = medical_transcription_with_comprehend(
            audio_file_uri=s3_uri,
            output_bucket_name=output_bucket_name,
            job_name_prefix=job_name_prefix,
            specialty=specialty,
            transcription_type=transcription_type,
            max_speakers=max_speakers,
            show_alternatives=show_alternatives,
            max_alternatives=max_alternatives,
            region_name=region_name
        )
        
        # Step 3: Optional cleanup
        if cleanup_s3_file:
            print("\nStep 3: Cleaning up uploaded file...")
            s3 = get_s3_client(region_name)
            s3_key = s3_uri.replace(f"s3://{bucket_name}/", "")
            s3.delete_object(Bucket=bucket_name, Key=s3_key)
            print(f"Deleted: {s3_uri}")
        
        # Add upload info to results
        results['source_file'] = {
            'local_path': local_file_path,
            's3_uri': s3_uri,
            'cleanup_performed': cleanup_s3_file
        }
        
        return results
        
    except Exception as e:
        print(f"Error processing local file: {str(e)}")
        raise

def upload_m4a_to_s3(local_file_path, bucket_name, s3_key, region_name="ap-southeast-2"):
    """
    Helper function to upload .m4a file to S3
    
    Args:
        local_file_path (str): Path to local .m4a file
        bucket_name (str): S3 bucket name
        s3_key (str): S3 object key (path/filename.m4a)
        region_name (str): AWS region
    
    Returns:
        str: S3 URI of uploaded file
    """
    s3 = get_s3_client(region_name)
    
    try:
        print(f"Uploading {local_file_path} to s3://{bucket_name}/{s3_key}")
        s3.upload_file(
            local_file_path, 
            bucket_name, 
            s3_key,
            ExtraArgs={'ContentType': 'audio/mp4'}  # Proper content type for .m4a
        )
        
        s3_uri = f"s3://{bucket_name}/{s3_key}"
        print(f"Upload completed: {s3_uri}")
        return s3_uri
        
    except Exception as e:
        raise Exception(f"Failed to upload file to S3: {str(e)}")

def print_analysis_summary(results):
    """Print a summary of the analysis results"""
    
    print("\n" + "="*80)
    print("MEDICAL TRANSCRIPTION AND ANALYSIS SUMMARY (.M4A)")
    print("="*80)
    
    print(f"\nJob Name: {results['transcription_job_name']}")
    print(f"Status: {results['transcription_status']}")
    print(f"Audio Format: {results['audio_format']}")
    
    print(f"\nFull Transcript ({len(results['full_transcript'])} characters):")
    print("-" * 50)
    print(results['full_transcript'][:500] + "..." if len(results['full_transcript']) > 500 else results['full_transcript'])
    
    print(f"\nSpeaker Segments ({len(results['speaker_segments'])} segments):")
    print("-" * 50)
    for segment in results['speaker_segments'][:3]:  # Show first 3 segments
        print(f"Speaker {segment['speaker']} ({segment['start_time']}s - {segment['end_time']}s):")
        print(f"  {segment['text'][:200]}{'...' if len(segment['text']) > 200 else ''}")
    
    print(f"\nMedical Entities Found: {len(results['medical_entities']['entities'])}")
    print("-" * 50)
    entity_types = {}
    for entity in results['medical_entities']['entities']:
        entity_type = entity['Type']
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
    
    for entity_type, count in sorted(entity_types.items()):
        print(f"  {entity_type}: {count}")
    
    print(f"\nPHI Entities Found: {len(results['phi_entities']['entities'])}")
    print("-" * 50)
    phi_types = {}
    for entity in results['phi_entities']['entities']:
        entity_type = entity['Type']
        phi_types[entity_type] = phi_types.get(entity_type, 0) + 1
    
    for phi_type, count in sorted(phi_types.items()):
        print(f"  {phi_type}: {count}")
    
    print(f"\nSpeaker-Specific Analysis:")
    print("-" * 50)
    for analysis in results['speaker_analysis'][:2]:  # Show first 2 speakers
        print(f"Speaker {analysis['speaker']}:")
        print(f"  Medical entities: {len(analysis['entities'])}")
        print(f"  PHI entities: {len(analysis['phi_entities'])}")

# Example usage for .m4a files
if __name__ == "__main__":
    # Configuration
    LOCAL_M4A_FILE = "/workspaces/AWS-Medical/transcribe/recordings/recording1.m4a"  # Replace with your local .m4a file path
    BUCKET_NAME = "askladmk43320la"  # Replace with your S3 bucket
    S3_KEY = "recordings/recording.m4a"  # S3 path for your file
    OUTPUT_BUCKET = "askladmk43320la"  # Replace with your output bucket
    REGION = "ap-southeast-2"  # Replace with your preferred region
    
    try:
        # Option 1: If file is already in S3
        # AUDIO_FILE_URI = f"s3://{BUCKET_NAME}/{S3_KEY}"
        
        # Option 2: Upload local .m4a file to S3 first
        print("Uploading .m4a file to S3...")
        AUDIO_FILE_URI = upload_m4a_to_s3(
            local_file_path=LOCAL_M4A_FILE,
            bucket_name=BUCKET_NAME,
            s3_key=S3_KEY,
            region_name=REGION
        )
        
        # Run the analysis
        print("\nStarting medical transcription and analysis...")
        results = medical_transcription_with_comprehend(
            audio_file_uri=AUDIO_FILE_URI,
            output_bucket_name=OUTPUT_BUCKET,
            job_name_prefix="m4a-medical-analysis",
            specialty="PRIMARYCARE",
            transcription_type="CONVERSATION",  # Use "DICTATION" for single speaker
            max_speakers=2,  # Adjust based on expected number of speakers
            region_name=REGION
        )
        
        # Print summary
        print_analysis_summary(results)
        
        # Save detailed results to file with dynamic IDs
        output_file = save_medical_analysis_results(results)
        
        print(f"\nDetailed results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
