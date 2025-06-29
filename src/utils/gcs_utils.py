import os
from google.cloud import storage

def _get_gcs_client():
    """Initializes and returns a GCS client."""
    return storage.Client()

def download_from_gcs(gcs_path, local_path):
    """
    Downloads a file or a directory from GCS to a local path.
    If gcs_path is a directory, it downloads all files in it.
    """
    client = _get_gcs_client()
    bucket_name, blob_prefix = gcs_path.replace("gs://", "").split("/", 1)
    bucket = client.bucket(bucket_name)
    
    blobs = bucket.list_blobs(prefix=blob_prefix)
    
    for blob in blobs:
        if blob.name.endswith('/'):
            continue
            
        destination_file_path = os.path.join(local_path, os.path.relpath(blob.name, blob_prefix))
        os.makedirs(os.path.dirname(destination_file_path), exist_ok=True)
        
        print(f"Downloading {blob.name} to {destination_file_path}...")
        blob.download_to_filename(destination_file_path)

def upload_to_gcs(local_path, gcs_path):
    """
    Uploads a file or a directory from a local path to GCS.
    If local_path is a directory, it uploads all files in it.
    """
    client = _get_gcs_client()
    bucket_name, blob_prefix = gcs_path.replace("gs://", "").split("/", 1)
    bucket = client.bucket(bucket_name)

    if os.path.isfile(local_path):
        blob_name = os.path.join(blob_prefix, os.path.basename(local_path))
        blob = bucket.blob(blob_name)
        print(f"Uploading {local_path} to gs://{bucket_name}/{blob_name}...")
        blob.upload_from_filename(local_path)
    else:
        for root, _, files in os.walk(local_path):
            for filename in files:
                local_file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(local_file_path, local_path)
                blob_name = os.path.join(blob_prefix, rel_path)
                
                blob = bucket.blob(blob_name)
                print(f"Uploading {local_file_path} to gs://{bucket_name}/{blob_name}...")
                blob.upload_from_filename(local_file_path)

def is_gcs_path(path):
    """Checks if a path is a GCS path."""
    return path.startswith("gs://")
