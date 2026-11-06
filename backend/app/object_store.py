from pathlib import Path

from .config import settings


class PrivateObjectStore:
    """Private storage. S3/MinIO in deployed environments, filesystem only for tests/dev."""

    def __init__(self):
        cfg = settings()
        self.bucket = cfg.object_store_bucket
        self.local = not (cfg.object_store_access_key and cfg.object_store_secret_key)
        if self.local:
            self.root = Path(cfg.local_storage_path)
            self.root.mkdir(parents=True, exist_ok=True)
        else:
            import boto3

            self.client = boto3.client(
                "s3",
                endpoint_url=cfg.object_store_endpoint,
                aws_access_key_id=cfg.object_store_access_key,
                aws_secret_access_key=cfg.object_store_secret_key,
                region_name=cfg.object_store_region,
            )
            try:
                self.client.head_bucket(Bucket=self.bucket)
            except Exception:
                self.client.create_bucket(Bucket=self.bucket)

    def put(self, key: str, body: bytes, media_type: str) -> None:
        if self.local:
            path = self.root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        else:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                ContentType=media_type,
                Metadata={"immutable": "true"},
            )

    def get(self, key: str) -> bytes:
        if self.local:
            return (self.root / key).read_bytes()
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()


def store() -> PrivateObjectStore:
    return PrivateObjectStore()
