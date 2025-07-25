import os, requests
import boto3
from fastapi import FastAPI, UploadFile, File, HTTPException
from botocore.exceptions import ClientError
from dotenv import load_dotenv
load_dotenv()
AWS_PROFILE = os.getenv("AWS_PROFILE")
S3_BUCKET = os.getenv("S3_BUCKET")
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")
NOTIFY_FROM = os.getenv("NOTIFY_FROM")

if not all([AWS_PROFILE, S3_BUCKET, MAILGUN_API_KEY, MAILGUN_DOMAIN, NOTIFY_FROM]):
    raise RuntimeError("Missing required environment variables")

app = FastAPI()
session = boto3.Session(profile_name=AWS_PROFILE)
s3 = session.client("s3")

def send_notification(to_email: str, filename: str, presigned_url: str):
    url = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages"
    try:
        resp = requests.post(
            url,
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": NOTIFY_FROM,
                "to": to_email,
                "subject": "Your file is ready",
                "text": f"File uploaded. Download here: {presigned_url}",
                "html": f"<p>Your file <strong>{filename}</strong> is available <a href='{presigned_url}'>here</a>.</p>"
            }
        )
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"[MAILGUN ERROR] Status: {resp.status_code}")
        print(f"[MAILGUN ERROR] Response: {resp.text}")
        raise e

@app.post("/upload/")
async def upload(file: UploadFile = File(...), notify_email: str = None):
    key = file.filename
    try:
        s3.upload_fileobj(file.file, S3_BUCKET, key)
        url = s3.generate_presigned_url("get_object", Params={"Bucket": S3_BUCKET,"Key": key}, ExpiresIn=3600)
        if notify_email:
            send_notification(notify_email, key, url)
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"filename": key, "download_url": url}

@app.get("/files/")
def list_files():
    resp = s3.list_objects_v2(Bucket=S3_BUCKET)
    return {"files": [o["Key"] for o in resp.get("Contents", [])]}

@app.delete("/files/{filename}")
def delete(filename: str):
    s3.delete_object(Bucket=S3_BUCKET, Key=filename)
    return {"deleted": filename}
