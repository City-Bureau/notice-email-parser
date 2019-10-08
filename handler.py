import os
from datetime import datetime
from email.parser import Parser
from email.policy import default

import boto3

S3_BUCKET = os.getenv("S3_BUCKET")


def match_akr_airport_authority(msg):
    sender = msg.get("reply-to", "") or msg.get("from", "")
    return "akroncantonairport.com" in sender.lower()


def match_akr_civil_rights(msg):
    # Verify that it's coming from an Akron government sender
    sender = msg.get("reply-to", "") or msg.get("from", "")
    if "akronohio.gov" not in sender.lower():
        return False

    # Check if ACRC is in the body, if so it's for ACRC
    for part in msg.iter_parts():
        if part.get_content_maintype() == "multipart":
            for sub_part in part.get_payload():
                if sub_part.get_content_maintype() == "text":
                    content = sub_part.get_content()
                    if "ACRC" in content:
                        return True

    # Otherwise check if ACRC is in the attachment name
    for attachment in msg.iter_attachments():
        attachment_name = attachment.get_filename().lower()
        if "civil rights" in attachment_name or "acrc" in attachment_name:
            return True

    return False


MATCHERS = {
    "akr_airport_authority": match_akr_airport_authority,
    "akr_civil_rights": match_akr_civil_rights,
}


def get_match(msg):
    for slug, matcher in MATCHERS.items():
        if matcher(msg):
            return slug


def handler(event, context):
    s3 = boto3.client("s3")
    rec = event["Records"][0]
    rec_dt = datetime.strptime(rec["eventTime"], "%Y-%m-%dT%H:%M:%S.%fZ")

    obj_source = {"Bucket": S3_BUCKET, "Key": rec["s3"]["object"]["key"]}
    obj = s3.get_object(**obj_source)
    msg = Parser(policy=default).parsestr(obj["Body"].read().decode("utf-8"))

    match_slug = get_match(msg)
    if not match_slug:
        sender = msg.get("reply-to", "") or msg.get("from", "")
        raise ValueError(f"Email {msg['subject']} from {sender} did not match")

    s3.copy_object(
        CopySource=obj_source,
        Bucket=S3_BUCKET,
        Key=f"{match_slug}/{rec_dt.strftime('%Y/%m/%d/%H%M')}.eml",
    )
    s3.copy_object(
        CopySource=obj_source, Bucket=S3_BUCKET, Key=f"{match_slug}/latest.eml"
    )
