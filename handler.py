import os
from datetime import datetime
from email.message import EmailMessage
from email.parser import Parser
from email.policy import default

import boto3
import sentry_sdk
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

S3_BUCKET = os.getenv("S3_BUCKET")


sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[AwsLambdaIntegration()],
    traces_sample_rate=1.0,
)


def get_sender(msg: EmailMessage) -> str:
    return str(msg.get("reply-to", "")) or str(msg.get("from", ""))


def match_akr_airport_authority(msg: EmailMessage) -> bool:
    return "akroncantonairport.com" in get_sender(msg).lower()


def match_akr_civil_rights(msg: EmailMessage) -> bool:
    # Verify that it's coming from an Akron government sender
    if "akronohio.gov" not in get_sender(msg).lower():
        return False

    # Check if ACRC is in the body, if so it's for ACRC
    for part in msg.iter_parts():
        if part.get_content_maintype() == "multipart":
            payload = part.get_payload()
            if not isinstance(payload, list):
                continue
            for sub_part in payload:
                if (
                    sub_part.get_content_maintype() == "text"
                    and not sub_part.is_multipart()
                ):
                    content = str(sub_part.get_payload(decode=True))
                    if "ACRC" in content or "Civil Rights" in content:
                        return True

    # Otherwise check if ACRC is in the attachment name
    for attachment in msg.iter_attachments():
        attachment_name = attachment.get_filename().lower()
        if any(p in attachment_name for p in ["civil rights", "civilrights", "acrc"]):
            return True

    return False


def match_akr_civil_service(msg: EmailMessage) -> bool:
    # Verify that it's coming from an Akron government sender
    if "akronohio.gov" not in get_sender(msg).lower():
        return False

    if "civil service" in str(msg.get("subject", "")).lower():
        return True

    # Check if "civil service" is in the body
    for part in msg.iter_parts():
        if part.get_content_maintype() == "multipart":
            payload = part.get_payload()
            if not isinstance(payload, list):
                continue
            for sub_part in payload:
                if (
                    sub_part.get_content_maintype() == "text"
                    and not sub_part.is_multipart()
                ):
                    content = str(sub_part.get_payload(decode=True))
                    if "civil service" in content.lower():
                        return True

    # Otherwise check if civil service is in the attachment name
    for attachment in msg.iter_attachments():
        attachment_name = attachment.get_filename().lower()
        if "civil service" in attachment_name:
            return True

    return False


def match_cuya_senior_transportation(msg: EmailMessage) -> bool:
    return "ridestc.org" in get_sender(msg).lower()


MATCHERS = {
    "akr_airport_authority": match_akr_airport_authority,
    "akr_civil_rights": match_akr_civil_rights,
    "akr_civil_service": match_akr_civil_service,
    "cuya_senior_transportation": match_cuya_senior_transportation,
}


def get_match(msg: EmailMessage) -> str:
    for slug, matcher in MATCHERS.items():
        if matcher(msg):
            return slug
    return ""


def handler(event, context):
    s3 = boto3.client("s3")
    rec = event["Records"][0]
    rec_dt = datetime.strptime(rec["eventTime"], "%Y-%m-%dT%H:%M:%S.%fZ")

    obj_source = {"Bucket": S3_BUCKET, "Key": rec["s3"]["object"]["key"]}
    obj = s3.get_object(**obj_source)
    msg = Parser(policy=default).parsestr(obj["Body"].read().decode("utf-8"))

    match_slug = get_match(msg)
    if match_slug == "":
        raise ValueError(f"Email {msg['subject']} from {get_sender(msg)} did not match")

    s3.copy_object(
        CopySource=obj_source,
        Bucket=S3_BUCKET,
        Key=f"{match_slug}/{rec_dt.strftime('%Y/%m/%d/%H%M')}.eml",
    )
    s3.copy_object(
        CopySource=obj_source, Bucket=S3_BUCKET, Key=f"{match_slug}/latest.eml"
    )
