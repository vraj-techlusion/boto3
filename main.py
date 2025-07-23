import os
import boto3
from fastapi import FastAPI, UploadFile, File, HTTPException
from botocore.exceptions import ClientError
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="AWS S3 File Upload API using Boto3")
BUCKET = os.getenv("S3_BUCKET")
print(f"Using S3 bucket: {BUCKET}")

PROFILE = os.getenv("AWS_PROFILE")
print(f"Using AWS profile: {PROFILE}")

session = boto3.Session(profile_name=PROFILE)
s3 = session.client("s3")

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """
    Uploads a file to an S3 bucket.

    Args:
        file: The file to be uploaded, passed as a `UploadFile` object.

    Returns:
        A JSON response with the uploaded filename.

    Raises:
        HTTPException: If there is an error uploading the file, a 500 status code
            is returned with the error message.
    """
    try:
        s3.upload_fileobj(file.file, BUCKET, file.filename)
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"filename": file.filename}

@app.get("/files")
def list_files():
    """
    Lists all files in the S3 bucket.

    Returns:
        A list of filenames (keys) from the S3 bucket.

    Raises:
        HTTPException: If there is an error retrieving the file list from S3.
    """

    resp = s3.list_objects_v2(Bucket=BUCKET)
    return [obj["Key"] for obj in resp.get("Contents", [])]

@app.get("/download/{filename}")
def download(filename: str):
    """
    Generates a presigned URL to download a file from S3.

    Args:
        filename: The name of the file to download.

    Returns:
        A JSON response with a single key "url", containing the presigned URL to
            download the file.

    Raises:
        HTTPException: If the file does not exist in the S3 bucket or if there
            is an error generating the presigned URL, a 404 status code is
            returned with the error message.
    """
    try:
        url = s3.generate_presigned_url('get_object',
                                        Params={'Bucket': BUCKET, 'Key': filename},
                                        ExpiresIn=3600)
    except ClientError as e:
        raise HTTPException(404, detail=str(e))
    return {"url": url}

@app.delete("/files/{filename}")
def delete_file(filename: str):
    """
    Deletes a file from the S3 bucket.

    Args:
        filename: The name of the file to delete.

    Returns:
        A JSON response with a single key "deleted", containing the name of the
            deleted file.

    Raises:
        HTTPException: If there is an error deleting the file from S3, a 500
            status code is returned with the error message.
    """

    try:
        s3.delete_object(Bucket=BUCKET, Key=filename)
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"deleted": filename}
