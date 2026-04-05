"""
model_storage.py — Model artifact storage with S3/MinIO support + local disk fallback.

Priority:
  1. S3/MinIO if MODEL_STORAGE_URL + MODEL_STORAGE_BUCKET + MODEL_STORAGE_KEY are set
  2. Local disk (default)

Usage:
  storage = ModelStorage()
  storage.save("model_v1.pkl", artifact_dict)
  artifact = storage.load("model_v1.pkl")
  storage.set_active("model_v1.pkl")
  active = storage.get_active()
"""

import os
import io
import json
from pathlib import Path
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from typing import Any

import joblib
from core.config import MODEL_PATH

# ── Storage backend selection ──
_MODEL_STORAGE_URL = os.environ.get("MODEL_STORAGE_URL", "").strip()
_MODEL_STORAGE_BUCKET = os.environ.get("MODEL_STORAGE_BUCKET", "").strip()
_MODEL_STORAGE_KEY = os.environ.get("MODEL_STORAGE_KEY", "").strip()
_MODEL_STORAGE_SECRET = os.environ.get("MODEL_STORAGE_SECRET", "").strip()


class ModelStorageBackend(ABC):
    """Abstract model storage backend."""

    @abstractmethod
    def save(self, name: str, artifact: dict) -> str:
        """Save model artifact, return storage path/identifier."""

    @abstractmethod
    def load(self, name: str) -> dict:
        """Load model artifact by name."""

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Check if model exists."""

    @abstractmethod
    def list_models(self) -> list[dict]:
        """List all stored models with metadata."""

    @abstractmethod
    def delete(self, name: str) -> bool:
        """Delete a model."""


class LocalDiskStorage(ModelStorageBackend):
    """Local filesystem storage with model registry file."""

    def __init__(self, base_dir: str = "models"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True, parents=True)
        self._registry_file = self.base_dir / "registry.json"
        self._registry: dict = self._load_registry()

    def _load_registry(self) -> dict:
        """Load registry from disk."""
        if self._registry_file.exists():
            try:
                with open(self._registry_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"models": {}, "active": None}
        return {"models": {}, "active": None}

    def _save_registry(self):
        """Save registry to disk atomically."""
        tmp = self._registry_file.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(self._registry, f, indent=2, ensure_ascii=False, default=str)
        os.replace(str(tmp), str(self._registry_file))

    def _model_path(self, name: str) -> Path:
        return self.base_dir / name

    def save(self, name: str, artifact: dict) -> str:
        path = self._model_path(name)
        tmp_path = path.with_suffix(".tmp")
        joblib.dump(artifact, tmp_path)
        os.replace(str(tmp_path), str(path))

        # Update registry
        metrics = artifact.get("metrics", {})
        repro = artifact.get("reproducibility", {})
        self._registry["models"][name] = {
            "name": name,
            "version": repro.get("model_version", "unknown"),
            "roc_auc": metrics.get("roc_auc"),
            "cv_auc_mean": metrics.get("cv_auc_mean"),
            "best_f1": metrics.get("best_f1"),
            "train_size": metrics.get("train_size"),
            "val_size": metrics.get("val_size"),
            "dataset_hash": repro.get("dataset_hash"),
            "seed": repro.get("seed"),
            "created_at": repro.get("training_timestamp", datetime.now(timezone.utc).isoformat()),
            "storage": "local",
            "path": str(path),
        }
        self._save_registry()
        return str(path)

    def load(self, name: str) -> dict:
        path = self._model_path(name)
        if not path.exists():
            raise FileNotFoundError(f"Model not found: {path}")
        return joblib.load(path)

    def exists(self, name: str) -> bool:
        return self._model_path(name).exists()

    def list_models(self) -> list[dict]:
        models = list(self._registry.get("models", {}).values())
        # Sort by created_at descending
        models.sort(key=lambda m: m.get("created_at", ""), reverse=True)
        return models

    def get_active(self) -> str | None:
        return self._registry.get("active")

    def set_active(self, name: str):
        if not self.exists(name):
            raise FileNotFoundError(f"Cannot activate non-existent model: {name}")
        prev = self._registry.get("active")
        self._registry["active"] = name
        self._registry["models"][name]["activated_at"] = datetime.now(timezone.utc).isoformat()
        self._registry["models"][name]["previous_active"] = prev
        self._save_registry()
        return prev

    def get_active_path(self) -> str | None:
        """Return the filesystem path of the active model."""
        active_name = self.get_active()
        if active_name and active_name in self._registry.get("models", {}):
            return self._registry["models"][active_name].get("path")
        return None

    def delete(self, name: str) -> bool:
        path = self._model_path(name)
        if path.exists():
            path.unlink()
        self._registry.get("models", {}).pop(name, None)
        if self._registry.get("active") == name:
            self._registry["active"] = None
        self._save_registry()
        return True

    def get_model_metadata(self, name: str) -> dict | None:
        return self._registry.get("models", {}).get(name)

    def rollback_active(self) -> str | None:
        """Rollback to the previous active model. Returns previous model name or None."""
        current = self.get_active()
        if current and current in self._registry.get("models", {}):
            prev = self._registry["models"][current].get("previous_active")
            if prev and self.exists(prev):
                self.set_active(prev)
                return prev
        return None


class S3Storage(ModelStorageBackend):
    """S3/MinIO storage for model artifacts.

    Requires: boto3 (pip install boto3)
    """

    def __init__(self, endpoint_url: str, bucket: str, access_key: str, secret_key: str):
        import boto3
        self.bucket = bucket
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self._local_registry = LocalDiskStorage()  # Registry always local for fast lookups

    def _s3_key(self, name: str) -> str:
        return f"models/{name}"

    def save(self, name: str, artifact: dict) -> str:
        data = io.BytesIO()
        joblib.dump(artifact, data)
        data.seek(0)

        self.s3.put_object(Bucket=self.bucket, Key=self._s3_key(name), Body=data.read())
        return f"s3://{self.bucket}/{self._s3_key(name)}"

    def load(self, name: str) -> dict:
        response = self.s3.get_object(Bucket=self.bucket, Key=self._s3_key(name))
        data = io.BytesIO(response["Body"].read())
        return joblib.load(data)

    def exists(self, name: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=self._s3_key(name))
            return True
        except Exception:
            return False

    def list_models(self) -> list[dict]:
        return self._local_registry.list_models()

    def get_active(self) -> str | None:
        return self._local_registry.get_active()

    def set_active(self, name: str):
        if not self.exists(name):
            raise FileNotFoundError(f"Cannot activate non-existent model in S3: {name}")
        return self._local_registry.set_active(name)

    def delete(self, name: str) -> bool:
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=self._s3_key(name))
        except Exception:
            pass
        return self._local_registry.delete(name)

    def get_active_path(self) -> str | None:
        """For S3, returns the S3 URI of the active model."""
        active_name = self.get_active()
        if active_name:
            return f"s3://{self.bucket}/{self._s3_key(active_name)}"
        return None

    def rollback_active(self) -> str | None:
        return self._local_registry.rollback_active()

    def get_model_metadata(self, name: str) -> dict | None:
        return self._local_registry.get_model_metadata(name)


# ── Factory ──

def create_model_storage() -> ModelStorageBackend:
    """Create the appropriate storage backend based on environment."""
    if _MODEL_STORAGE_URL and _MODEL_STORAGE_BUCKET and _MODEL_STORAGE_KEY:
        try:
            return S3Storage(
                endpoint_url=_MODEL_STORAGE_URL,
                bucket=_MODEL_STORAGE_BUCKET,
                access_key=_MODEL_STORAGE_KEY,
                secret_key=_MODEL_STORAGE_SECRET,
            )
        except ImportError:
            print("[WARN] boto3 not installed — falling back to local disk storage")
    return LocalDiskStorage()


# Module-level singleton
_storage: ModelStorageBackend | None = None


def get_storage() -> ModelStorageBackend:
    """Get or create the storage singleton."""
    global _storage
    if _storage is None:
        _storage = create_model_storage()
    return _storage
