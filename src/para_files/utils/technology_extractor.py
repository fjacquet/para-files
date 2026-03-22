"""Technology extraction using semantic matching.

Extracts technology/topic category from document content or filename
using Ollama embeddings (via litellm) for semantic similarity matching.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger


if TYPE_CHECKING:
    from para_files.encoders.ollama_encoder import OllamaEncoder


# Minimum similarity score to consider a technology match
TECHNOLOGY_MATCH_THRESHOLD = 0.45

# Technology descriptions for semantic matching
# These are expanded descriptions that help the embedding model understand context
TECHNOLOGY_DESCRIPTIONS: dict[str, list[str]] = {
    # === Databases ===
    "MariaDB": ["MariaDB database MySQL SQL relational database server"],
    "MySQL": ["MySQL database SQL relational database management"],
    "Oracle": ["Oracle Database RAC Real Application Clusters enterprise database"],
    "PostgreSQL": ["PostgreSQL Postgres database SQL open source"],
    "MongoDB": ["MongoDB NoSQL document database"],
    "Redis": ["Redis cache in-memory data store"],
    # === Container/Cloud Platforms ===
    "Kubernetes": ["Kubernetes K8s container orchestration pods deployments"],
    "OpenShift": ["Red Hat OpenShift container platform Kubernetes enterprise OCP"],
    "OpenStack": ["OpenStack cloud platform infrastructure IaaS Nova Cinder Swift"],
    "EKS": ["Amazon EKS Elastic Kubernetes Service AWS containers"],
    "Docker": ["Docker containers containerization images"],
    # === VMware ===
    "VMware": ["VMware vSphere ESXi virtualization virtual machines hypervisor"],
    "vSphere": ["VMware vSphere ESXi vCenter virtualization"],
    "vSAN": ["VMware vSAN virtual storage area network"],
    "NSX": ["VMware NSX network virtualization software-defined networking"],
    "Tanzu": ["VMware Tanzu Kubernetes platform cloud native"],
    # === Dell Storage (Current) ===
    "PowerMax": ["Dell PowerMax enterprise storage array NVMe HYPERMAX VMAX successor"],
    "PowerStore": ["Dell PowerStore midrange storage array block file NVMe"],
    "PowerScale": ["Dell PowerScale scale-out NAS file storage Isilon successor"],
    "PowerFlex": ["Dell PowerFlex software-defined storage SDS block ScaleIO"],
    "PowerVault": ["Dell PowerVault entry storage DAS direct attached"],
    "Unity": ["Dell EMC Unity midrange storage array block file VNX successor"],
    "ObjectScale": ["Dell ObjectScale S3 object storage ECS cloud native"],
    "ECS": ["Dell EMC ECS Elastic Cloud Storage object S3 compatible"],
    # === Dell Data Protection ===
    "PowerProtect": ["Dell PowerProtect data protection backup appliance DD"],
    "DataDomain": ["Dell EMC Data Domain deduplication backup appliance DD Boost"],
    "Avamar": ["Dell EMC Avamar backup deduplication software virtual"],
    "NetWorker": ["Dell EMC NetWorker backup recovery enterprise software"],
    "RecoverPoint": ["Dell EMC RecoverPoint continuous data protection CDP replication"],
    "AppSync": ["Dell EMC AppSync copy data management snapshot orchestration"],
    "CyberRecovery": ["Dell PowerProtect Cyber Recovery vault ransomware isolation"],
    # === Dell Legacy Storage ===
    "VMAX": ["Dell EMC VMAX Symmetrix enterprise storage array high-end"],
    "Symmetrix": ["EMC Symmetrix DMX VMAX enterprise storage mainframe"],
    "VNX": ["Dell EMC VNX unified storage array block file midrange"],
    "CLARiiON": ["EMC CLARiiON CX storage array block SAN FC"],
    "Isilon": ["Dell EMC Isilon scale-out NAS file storage cluster"],
    "XtremIO": ["Dell EMC XtremIO all-flash array AFA inline deduplication"],
    "VPLEX": ["Dell EMC VPLEX federation virtualization metro geo active-active"],
    "ViPR": ["Dell EMC ViPR software-defined storage SDS controller"],
    "Celerra": ["EMC Celerra NAS file storage gateway unified"],
    "Centera": ["EMC Centera CAS content-addressed storage archive"],
    "Atmos": ["EMC Atmos cloud storage object platform"],
    # === Dell HCI/Converged ===
    "VxRail": ["Dell VxRail hyperconverged infrastructure HCI VMware appliance"],
    "VxRack": ["Dell EMC VxRack rack-scale infrastructure ScaleIO FLEX"],
    "VxBlock": ["Dell EMC VxBlock converged infrastructure CI Vblock"],
    # === Dell Networking ===
    "Connectrix": ["Dell EMC Connectrix SAN switch director Brocade FC"],
    "SONiC": ["Dell SONiC network operating system open source switching"],
    "PowerSwitch": ["Dell PowerSwitch network switches data center fabric"],
    # === Dell Cloud/APEX ===
    "APEX": ["Dell APEX as-a-service cloud consumption storage compute"],
    # === Compute/GPU ===
    "GPU": ["GPU graphics processing unit NVIDIA CUDA accelerated computing"],
    "NVIDIA": ["NVIDIA GPU graphics card CUDA deep learning AI acceleration"],
    "AI": ["artificial intelligence machine learning deep learning neural networks"],
    # === Programming ===
    "Python": ["Python programming language development"],
    "Go": ["Go Golang programming language"],
    "Java": ["Java programming language JVM enterprise"],
    # === Automation ===
    "Ansible": ["Ansible automation configuration management playbooks"],
    "Terraform": ["Terraform infrastructure as code IaC provisioning"],
    # === General Categories ===
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
        self._encoder: OllamaEncoder | None = None
        self._tech_embeddings: list[list[float]] | None = None

    def _get_encoder(self) -> OllamaEncoder | None:
        """Lazy-load the Ollama encoder."""
        if self._encoder is None:
            try:
                from para_files.encoders import OllamaEncoder

                self._encoder = OllamaEncoder()
            except ImportError:
                logger.warning("Ollama encoder not available for technology detection")
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
        except (ValueError, KeyError, OSError, RuntimeError) as e:
            logger.exception("Failed to compute technology embeddings: {}", e)
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
            # Limit to 400 chars to stay safely under MLX model's 512 token limit
            # (some texts tokenize poorly, e.g., 700 chars → 800+ tokens)
            doc_embedding = encoder([content[:400]])[0]

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

        except (ValueError, KeyError, OSError, RuntimeError) as e:
            logger.exception("Error in semantic technology extraction: {}", e)

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
            # Databases
            "mariadb": "MariaDB",
            "maria db": "MariaDB",
            "mysql": "MySQL",
            "oracle": "Oracle",
            "rac": "Oracle",  # RAC is Oracle-specific
            "postgres": "PostgreSQL",
            "postgresql": "PostgreSQL",
            "mongodb": "MongoDB",
            "redis": "Redis",
            # Container/Cloud Platforms
            "k8s": "Kubernetes",
            "kubernetes": "Kubernetes",
            "eks": "EKS",
            "openshift": "OpenShift",
            "ocp": "OpenShift",
            "openstack": "OpenStack",  # NOT OpenShift!
            "nova": "OpenStack",
            "cinder": "OpenStack",
            "docker": "Docker",
            # VMware
            "vmware": "VMware",
            "vsphere": "vSphere",
            "esxi": "VMware",
            "vcenter": "vSphere",
            "vsan": "vSAN",
            "nsx": "NSX",
            "tanzu": "Tanzu",
            # Dell Storage (Current)
            "powermax": "PowerMax",
            "hypermax": "PowerMax",
            "powerstore": "PowerStore",
            "powerscale": "PowerScale",
            "powerflex": "PowerFlex",
            "scaleio": "PowerFlex",
            "powervault": "PowerVault",
            "unity": "Unity",
            "objectscale": "ObjectScale",
            "ecs": "ECS",
            # Dell Data Protection
            "powerprotect": "PowerProtect",
            "data domain": "DataDomain",
            "datadomain": "DataDomain",
            "dd boost": "DataDomain",
            "ddboost": "DataDomain",
            "avamar": "Avamar",
            "networker": "NetWorker",
            "recoverpoint": "RecoverPoint",
            "appsync": "AppSync",
            "cyber recovery": "CyberRecovery",
            "cyberrecovery": "CyberRecovery",
            # Dell Legacy Storage
            "vmax": "VMAX",
            "symmetrix": "Symmetrix",
            "dmx": "Symmetrix",
            "vnx": "VNX",
            "vnxe": "VNX",
            "clariion": "CLARiiON",
            "isilon": "Isilon",
            "xtremio": "XtremIO",
            "vplex": "VPLEX",
            "vipr": "ViPR",
            "celerra": "Celerra",
            "centera": "Centera",
            "atmos": "Atmos",
            # Dell HCI/Converged
            "vxrail": "VxRail",
            "vxrack": "VxRack",
            "vxblock": "VxBlock",
            "vblock": "VxBlock",
            # Dell Networking
            "connectrix": "Connectrix",
            "sonic": "SONiC",
            "powerswitch": "PowerSwitch",
            # Dell Cloud
            "apex": "APEX",
            # Compute/GPU
            "gpu": "GPU",
            "nvidia": "NVIDIA",
            "cuda": "NVIDIA",
            # Automation
            "ansible": "Ansible",
            "terraform": "Terraform",
            # Programming
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
            logger.debug("Technology from filename: {}", tech)
            return tech, 0.95, "filename"

        # Try content-based if available
        if content:
            tech, score = self.extract_from_content(content)
            if tech:
                logger.debug("Technology from content: {} ({:.2f})", tech, score)
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
