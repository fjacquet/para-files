"""Technology extraction using MLX semantic matching.

Extracts technology/topic category from document content or filename
using MLX embeddings for semantic similarity matching.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from para_files.encoders.mlx_encoder import MLXEncoder

logger = logging.getLogger(__name__)

# Minimum similarity score to consider a technology match
TECHNOLOGY_MATCH_THRESHOLD = 0.45

# Technology descriptions for semantic matching
# These are expanded descriptions that help the embedding model understand context
TECHNOLOGY_DESCRIPTIONS: dict[str, list[str]] = {
    "MariaDB": ["MariaDB database MySQL SQL relational database server"],
    "MySQL": ["MySQL database SQL relational database management"],
    "Oracle": ["Oracle Database RAC Real Application Clusters enterprise database"],
    "PostgreSQL": ["PostgreSQL Postgres database SQL open source"],
    "MongoDB": ["MongoDB NoSQL document database"],
    "Redis": ["Redis cache in-memory data store"],
    "Kubernetes": ["Kubernetes K8s container orchestration pods deployments"],
    "OpenShift": ["Red Hat OpenShift container platform Kubernetes enterprise"],
    "EKS": ["Amazon EKS Elastic Kubernetes Service AWS containers"],
    "Docker": ["Docker containers containerization images"],
    "VMware": ["VMware vSphere ESXi virtualization virtual machines hypervisor"],
    "vSphere": ["VMware vSphere ESXi vCenter virtualization"],
    "vSAN": ["VMware vSAN virtual storage area network"],
    "NSX": ["VMware NSX network virtualization software-defined networking"],
    "Tanzu": ["VMware Tanzu Kubernetes platform cloud native"],
    "GPU": ["GPU graphics processing unit NVIDIA CUDA accelerated computing"],
    "NVIDIA": ["NVIDIA GPU graphics card CUDA deep learning AI acceleration"],
    "AI": ["artificial intelligence machine learning deep learning neural networks"],
    "Python": ["Python programming language development"],
    "Go": ["Go Golang programming language"],
    "Java": ["Java programming language JVM enterprise"],
    "Ansible": ["Ansible automation configuration management playbooks"],
    "Terraform": ["Terraform infrastructure as code IaC provisioning"],
    "PowerFlex": ["Dell PowerFlex software-defined storage ScaleIO"],
    "PowerStore": ["Dell PowerStore storage array enterprise"],
    "VxRail": ["Dell VxRail hyperconverged infrastructure HCI VMware"],
    "Storage": ["storage SAN NAS block file object data"],
    "Backup": ["backup recovery data protection disaster recovery"],
    "Security": ["security cybersecurity encryption authentication"],
    "Networking": ["networking network switches routers firewall"],
    "Cloud": ["cloud computing AWS Azure GCP public cloud"],
    "Linux": ["Linux operating system Ubuntu RedHat CentOS"],
    "Windows": ["Windows Server Microsoft operating system"],
}


class TechnologyExtractor:
    """Extract technology category from documents using MLX embeddings."""

    def __init__(
        self,
        technologies: list[str] | None = None,
        threshold: float = TECHNOLOGY_MATCH_THRESHOLD,
    ) -> None:
        """Initialize the technology extractor.

        Args:
            technologies: List of technology names to match against.
                         If None, uses keys from TECHNOLOGY_DESCRIPTIONS.
            threshold: Minimum similarity score for a match.
        """
        self._technologies = technologies or list(TECHNOLOGY_DESCRIPTIONS.keys())
        self._threshold = threshold
        self._encoder: MLXEncoder | None = None
        self._tech_embeddings: list[list[float]] | None = None

    def _get_encoder(self) -> MLXEncoder | None:
        """Lazy-load the MLX encoder."""
        if self._encoder is None:
            try:
                from para_files.encoders import MLXEncoder

                self._encoder = MLXEncoder()
            except ImportError:
                logger.warning("MLX encoder not available for technology detection")
        return self._encoder

    def _ensure_tech_embeddings(self) -> bool:
        """Pre-compute embeddings for all technologies.

        Returns:
            True if embeddings are available, False otherwise.
        """
        if self._tech_embeddings is not None:
            return True

        encoder = self._get_encoder()
        if encoder is None:
            return False

        # Build descriptions for each technology
        descriptions = []
        for tech in self._technologies:
            if tech in TECHNOLOGY_DESCRIPTIONS:
                descriptions.append(" ".join(TECHNOLOGY_DESCRIPTIONS[tech]))
            else:
                # Use the technology name itself as description
                descriptions.append(tech)

        try:
            self._tech_embeddings = encoder(descriptions)
        except Exception:
            logger.exception("Failed to compute technology embeddings")
            return False
        else:
            return True

    def extract_from_content(self, content: str) -> tuple[str | None, float]:
        """Extract technology from document content using semantic matching.

        Args:
            content: Document content to analyze.

        Returns:
            Tuple of (technology_name, confidence_score) or (None, 0.0).
        """
        if not content or not self._ensure_tech_embeddings():
            return None, 0.0

        encoder = self._get_encoder()
        if encoder is None or self._tech_embeddings is None:
            return None, 0.0

        try:
            import numpy as np

            # Encode document content
            doc_embedding = encoder([content[:2000]])[0]  # Limit content length

            # Calculate cosine similarity with each technology
            doc_vec = np.array(doc_embedding)
            similarities = []
            for tech_emb in self._tech_embeddings:
                tech_vec = np.array(tech_emb)
                similarity = float(
                    np.dot(doc_vec, tech_vec)
                    / (np.linalg.norm(doc_vec) * np.linalg.norm(tech_vec) + 1e-9)
                )
                similarities.append(similarity)

            # Find best match
            best_idx = int(np.argmax(similarities))
            best_score = similarities[best_idx]

            if best_score >= self._threshold:
                return self._technologies[best_idx], best_score

        except Exception:
            logger.exception("Error in semantic technology extraction")

        return None, 0.0

    def extract_from_filename(self, filename: str) -> str | None:
        """Extract technology from filename using pattern matching.

        This is a fast fallback that doesn't require MLX.

        Args:
            filename: Filename to analyze.

        Returns:
            Technology name or None.
        """
        # Normalize filename for matching
        name_lower = filename.lower().replace("_", " ").replace("-", " ")

        # Direct technology name matching (case-insensitive)
        for tech in self._technologies:
            # Create pattern that matches the technology name as a word
            pattern = rf"\b{re.escape(tech.lower())}\b"
            if re.search(pattern, name_lower):
                return tech

        # Additional keyword mappings for common variations
        keyword_to_tech = {
            "mariadb": "MariaDB",
            "maria db": "MariaDB",
            "mysql": "MySQL",
            "oracle": "Oracle",
            "rac": "Oracle",  # RAC is Oracle-specific
            "postgres": "PostgreSQL",
            "postgresql": "PostgreSQL",
            "k8s": "Kubernetes",
            "kubernetes": "Kubernetes",
            "eks": "EKS",
            "openshift": "OpenShift",
            "ocp": "OpenShift",
            "docker": "Docker",
            "vmware": "VMware",
            "vsphere": "vSphere",
            "esxi": "VMware",
            "vsan": "vSAN",
            "nsx": "NSX",
            "tanzu": "Tanzu",
            "gpu": "GPU",
            "nvidia": "NVIDIA",
            "cuda": "NVIDIA",
            "powerflex": "PowerFlex",
            "scaleio": "PowerFlex",
            "powerstore": "PowerStore",
            "vxrail": "VxRail",
            "ansible": "Ansible",
            "terraform": "Terraform",
            "python": "Python",
            "golang": "Go",
        }

        for keyword, tech in keyword_to_tech.items():
            # Use word boundary matching to avoid false positives
            # e.g., "rac" should not match "Practices"
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, name_lower):
                return tech

        return None

    def extract(
        self,
        file_path: Path,
        content: str | None = None,
    ) -> tuple[str | None, float, str]:
        """Extract technology from file using multiple strategies.

        Tries filename matching first (fast), then content-based (accurate).

        Args:
            file_path: Path to the file.
            content: Optional pre-extracted content.

        Returns:
            Tuple of (technology, confidence, source) where source is
            'filename' or 'content'.
        """
        # Try filename first (fast, deterministic)
        tech = self.extract_from_filename(file_path.name)
        if tech:
            logger.debug("Technology from filename: %s", tech)
            return tech, 0.95, "filename"

        # Try content-based if available
        if content:
            tech, score = self.extract_from_content(content)
            if tech:
                logger.debug("Technology from content: %s (%.2f)", tech, score)
                return tech, score, "content"

        return None, 0.0, "none"


def extract_technology(
    file_path: Path,
    content: str | None = None,
    technologies: list[str] | None = None,
) -> str | None:
    """Convenience function to extract technology from a file.

    Args:
        file_path: Path to the file.
        content: Optional pre-extracted content.
        technologies: Optional list of technologies to match against.

    Returns:
        Technology name or None.
    """
    extractor = TechnologyExtractor(technologies=technologies)
    tech, _, _ = extractor.extract(file_path, content)
    return tech
