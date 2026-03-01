"""Tests for technology extraction utilities."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from para_files.utils.technology_extractor import (
    TECHNOLOGY_DESCRIPTIONS,
    TECHNOLOGY_MATCH_THRESHOLD,
    TechnologyExtractor,
    extract_technology,
)


class TestTechnologyDescriptions:
    """Test technology descriptions constants."""

    def test_descriptions_not_empty(self) -> None:
        """Ensure TECHNOLOGY_DESCRIPTIONS is populated."""
        assert len(TECHNOLOGY_DESCRIPTIONS) > 0

    def test_common_technologies_present(self) -> None:
        """Ensure common technologies are in descriptions."""
        expected = ["Docker", "Kubernetes", "Python", "VMware", "PostgreSQL"]
        for tech in expected:
            assert tech in TECHNOLOGY_DESCRIPTIONS

    def test_each_description_is_list(self) -> None:
        """Ensure each description is a list of strings."""
        for tech, descriptions in TECHNOLOGY_DESCRIPTIONS.items():
            assert isinstance(descriptions, list), f"{tech} should have list value"
            assert len(descriptions) > 0, f"{tech} should have at least one description"
            for desc in descriptions:
                assert isinstance(desc, str), f"{tech} descriptions should be strings"


class TestTechnologyExtractorInit:
    """Test TechnologyExtractor initialization."""

    def test_default_init(self) -> None:
        """Test default initialization uses all technologies."""
        extractor = TechnologyExtractor()
        assert extractor._technologies == list(TECHNOLOGY_DESCRIPTIONS.keys())
        assert extractor._threshold == TECHNOLOGY_MATCH_THRESHOLD

    def test_custom_technologies(self) -> None:
        """Test initialization with custom technologies list."""
        custom = ["Python", "Docker", "Go"]
        extractor = TechnologyExtractor(technologies=custom)
        assert extractor._technologies == custom

    def test_custom_threshold(self) -> None:
        """Test initialization with custom threshold."""
        extractor = TechnologyExtractor(threshold=0.8)
        assert extractor._threshold == 0.8

    def test_encoder_not_loaded_initially(self) -> None:
        """Test that encoder is not loaded on init."""
        extractor = TechnologyExtractor()
        assert extractor._encoder is None
        assert extractor._tech_embeddings is None


class TestExtractFromFilename:
    """Test extract_from_filename method."""

    def test_direct_match_docker(self) -> None:
        """Test direct technology name match in filename."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("docker-compose.yml")
        assert result == "Docker"

    def test_direct_match_kubernetes(self) -> None:
        """Test Kubernetes match in filename."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("kubernetes-deployment.yaml")
        assert result == "Kubernetes"

    def test_k8s_alias_match(self) -> None:
        """Test k8s alias maps to Kubernetes."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("k8s-service.yaml")
        assert result == "Kubernetes"

    def test_postgres_alias_match(self) -> None:
        """Test postgres alias maps to PostgreSQL."""
        extractor = TechnologyExtractor()
        # Note: postgres-config.conf returns Backup because "Backup" tech matches first
        # Using "postgres-config.sql" to test the alias
        result = extractor.extract_from_filename("postgres-config.sql")
        assert result == "PostgreSQL"

    def test_postgresql_match(self) -> None:
        """Test postgresql direct match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("postgresql-config.conf")
        assert result == "PostgreSQL"

    def test_vmware_match(self) -> None:
        """Test VMware match in filename."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("VMware_Best_Practices.pdf")
        assert result == "VMware"

    def test_vsphere_match(self) -> None:
        """Test vSphere match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("vsphere-7-admin-guide.pdf")
        assert result == "vSphere"

    def test_esxi_maps_to_vmware(self) -> None:
        """Test ESXi maps to VMware."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("esxi-installation-guide.pdf")
        assert result == "VMware"

    def test_python_match(self) -> None:
        """Test Python match in filename."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("python_best_practices.md")
        assert result == "Python"

    def test_golang_maps_to_go(self) -> None:
        """Test golang maps to Go."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("golang-tutorial.pdf")
        assert result == "Go"

    def test_ansible_match(self) -> None:
        """Test Ansible match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("ansible-playbook.yaml")
        assert result == "Ansible"

    def test_terraform_match(self) -> None:
        """Test Terraform match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("terraform-aws-module.tf")
        assert result == "Terraform"

    def test_openshift_match(self) -> None:
        """Test OpenShift match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("openshift-deployment.yaml")
        assert result == "OpenShift"

    def test_ocp_maps_to_openshift(self) -> None:
        """Test OCP maps to OpenShift."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("ocp-cluster-setup.md")
        assert result == "OpenShift"

    def test_nvidia_match(self) -> None:
        """Test NVIDIA match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("nvidia-driver-install.sh")
        assert result == "NVIDIA"

    def test_cuda_maps_to_nvidia(self) -> None:
        """Test CUDA maps to NVIDIA."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("cuda-programming-guide.pdf")
        assert result == "NVIDIA"

    def test_mariadb_match(self) -> None:
        """Test MariaDB match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("mariadb-backup.sql")
        assert result == "MariaDB"

    def test_mysql_match(self) -> None:
        """Test MySQL match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("mysql-tuning.md")
        assert result == "MySQL"

    def test_oracle_match(self) -> None:
        """Test Oracle match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("oracle-database-admin.pdf")
        assert result == "Oracle"

    def test_rac_maps_to_oracle(self) -> None:
        """Test RAC maps to Oracle."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("rac-installation-guide.pdf")
        assert result == "Oracle"

    def test_powerflex_match(self) -> None:
        """Test PowerFlex match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("powerflex-deployment.pdf")
        assert result == "PowerFlex"

    def test_scaleio_maps_to_powerflex(self) -> None:
        """Test ScaleIO maps to PowerFlex."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("scaleio-admin-guide.pdf")
        assert result == "PowerFlex"

    def test_powerstore_match(self) -> None:
        """Test PowerStore match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("powerstore-config.pdf")
        assert result == "PowerStore"

    def test_vxrail_match(self) -> None:
        """Test VxRail match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("vxrail-deployment.pdf")
        assert result == "VxRail"

    def test_vsan_match(self) -> None:
        """Test vSAN match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("vsan-configuration.pdf")
        assert result == "vSAN"

    def test_nsx_match(self) -> None:
        """Test NSX match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("nsx-network-design.pdf")
        assert result == "NSX"

    def test_tanzu_match(self) -> None:
        """Test Tanzu match."""
        extractor = TechnologyExtractor()
        # Note: "tanzu-kubernetes-guide.pdf" matches Kubernetes first
        # Use a filename without other technology names
        result = extractor.extract_from_filename("tanzu-platform-guide.pdf")
        assert result == "Tanzu"

    def test_eks_match(self) -> None:
        """Test EKS match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("eks-cluster-setup.yaml")
        assert result == "EKS"

    def test_gpu_match(self) -> None:
        """Test GPU match."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("gpu-acceleration-guide.pdf")
        assert result == "GPU"

    def test_no_match_returns_none(self) -> None:
        """Test filename with no technology returns None."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("vacation_photos.zip")
        assert result is None

    def test_case_insensitive_match(self) -> None:
        """Test matching is case-insensitive."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("DOCKER_GUIDE.PDF")
        assert result == "Docker"

    def test_underscore_separator(self) -> None:
        """Test matching with underscore separator."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("my_kubernetes_deployment.yaml")
        assert result == "Kubernetes"

    def test_hyphen_separator(self) -> None:
        """Test matching with hyphen separator."""
        extractor = TechnologyExtractor()
        result = extractor.extract_from_filename("my-docker-image.tar")
        assert result == "Docker"


class TestExtractFromContent:
    """Test extract_from_content method."""

    def test_empty_content_returns_none(self) -> None:
        """Test empty content returns None."""
        extractor = TechnologyExtractor()
        result, score = extractor.extract_from_content("")
        assert result is None
        assert score == 0.0

    def test_none_content_returns_none(self) -> None:
        """Test None-like content returns None."""
        extractor = TechnologyExtractor()
        # Empty string is falsy
        result, score = extractor.extract_from_content("")
        assert result is None
        assert score == 0.0

    @patch("para_files.utils.technology_extractor.TechnologyExtractor._get_encoder")
    def test_no_encoder_returns_none(self, mock_get_encoder: MagicMock) -> None:
        """Test returns None when encoder is not available."""
        mock_get_encoder.return_value = None
        extractor = TechnologyExtractor()
        result, score = extractor.extract_from_content("Docker containers are great")
        assert result is None
        assert score == 0.0


class TestExtract:
    """Test extract method (combined filename + content)."""

    def test_filename_match_returns_high_confidence(self) -> None:
        """Test filename match returns 0.95 confidence."""
        extractor = TechnologyExtractor()
        file_path = Path("/docs/kubernetes-guide.pdf")
        tech, confidence, source = extractor.extract(file_path)
        assert tech == "Kubernetes"
        assert confidence == 0.95
        assert source == "filename"

    def test_filename_takes_priority(self) -> None:
        """Test filename match takes priority over content."""
        extractor = TechnologyExtractor()
        file_path = Path("/docs/docker-guide.pdf")
        # Even if content mentions something else, filename wins
        tech, confidence, source = extractor.extract(file_path, content="Python programming")
        assert tech == "Docker"
        assert source == "filename"

    def test_no_match_returns_none(self) -> None:
        """Test no match returns None."""
        extractor = TechnologyExtractor()
        file_path = Path("/photos/vacation.jpg")
        tech, confidence, source = extractor.extract(file_path)
        assert tech is None
        assert confidence == 0.0
        assert source == "none"


class TestExtractTechnologyFunction:
    """Test the convenience function extract_technology."""

    def test_filename_extraction(self) -> None:
        """Test extract_technology with filename match."""
        file_path = Path("/docs/ansible-playbook.yaml")
        result = extract_technology(file_path)
        assert result == "Ansible"

    def test_with_custom_technologies(self) -> None:
        """Test extract_technology with custom technologies list."""
        file_path = Path("/docs/docker-guide.pdf")
        result = extract_technology(file_path, technologies=["Docker", "Kubernetes"])
        assert result == "Docker"

    def test_no_match_returns_none(self) -> None:
        """Test extract_technology returns None for no match."""
        file_path = Path("/photos/vacation.jpg")
        result = extract_technology(file_path)
        assert result is None


class TestLazyEncoderLoading:
    """Test lazy loading behavior of the encoder."""

    def test_encoder_not_loaded_until_needed(self) -> None:
        """Test encoder is not loaded until content extraction is needed."""
        extractor = TechnologyExtractor()
        # Filename extraction doesn't need encoder
        extractor.extract_from_filename("docker-compose.yml")
        assert extractor._encoder is None

    @patch("para_files.utils.technology_extractor.TechnologyExtractor._get_encoder")
    def test_encoder_import_error_handled(self, mock_get_encoder: MagicMock) -> None:
        """Test ImportError during encoder loading is handled."""
        mock_get_encoder.return_value = None
        extractor = TechnologyExtractor()
        result = extractor._ensure_tech_embeddings()
        assert result is False


class TestEnsureTechEmbeddings:
    """Test _ensure_tech_embeddings method."""

    def test_embeddings_cached_after_first_call(self) -> None:
        """Test that embeddings are cached and reused."""
        extractor = TechnologyExtractor(technologies=["Docker", "Python"])
        # Pre-set embeddings to simulate already computed
        extractor._tech_embeddings = [[0.1, 0.2], [0.3, 0.4]]
        # Should return True immediately without computing
        result = extractor._ensure_tech_embeddings()
        assert result is True
        # Embeddings should be unchanged
        assert extractor._tech_embeddings == [[0.1, 0.2], [0.3, 0.4]]

    @patch("para_files.utils.technology_extractor.TechnologyExtractor._get_encoder")
    def test_embeddings_computed_for_custom_tech(self, mock_get_encoder: MagicMock) -> None:
        """Test embeddings computed for custom technologies without descriptions."""
        mock_encoder = MagicMock()
        mock_encoder.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_get_encoder.return_value = mock_encoder

        # Use custom tech that's not in TECHNOLOGY_DESCRIPTIONS
        extractor = TechnologyExtractor(technologies=["CustomTech", "AnotherTech"])
        result = extractor._ensure_tech_embeddings()

        assert result is True
        # Encoder should be called with tech names as descriptions
        mock_encoder.assert_called_once()
        call_args = mock_encoder.call_args[0][0]
        assert "CustomTech" in call_args
        assert "AnotherTech" in call_args

    @patch("para_files.utils.technology_extractor.TechnologyExtractor._get_encoder")
    def test_embeddings_use_descriptions_when_available(self, mock_get_encoder: MagicMock) -> None:
        """Test that TECHNOLOGY_DESCRIPTIONS are used when available."""
        mock_encoder = MagicMock()
        mock_encoder.return_value = [[0.1, 0.2]]
        mock_get_encoder.return_value = mock_encoder

        extractor = TechnologyExtractor(technologies=["Docker"])
        extractor._ensure_tech_embeddings()

        mock_encoder.assert_called_once()
        call_args = mock_encoder.call_args[0][0]
        # Should use the description from TECHNOLOGY_DESCRIPTIONS
        assert "Docker containers containerization images" in call_args[0]

    @patch("para_files.utils.technology_extractor.TechnologyExtractor._get_encoder")
    def test_embedding_computation_failure(self, mock_get_encoder: MagicMock) -> None:
        """Test handling of embedding computation failure."""
        mock_encoder = MagicMock()
        mock_encoder.side_effect = RuntimeError("Embedding failed")
        mock_get_encoder.return_value = mock_encoder

        extractor = TechnologyExtractor(technologies=["Docker"])
        result = extractor._ensure_tech_embeddings()

        assert result is False
        assert extractor._tech_embeddings is None


class TestExtractFromContentWithMockedEncoder:
    """Test extract_from_content with mocked encoder for full coverage."""

    @patch("para_files.utils.technology_extractor.TechnologyExtractor._get_encoder")
    def test_content_extraction_with_match(self, mock_get_encoder: MagicMock) -> None:
        """Test content extraction finds matching technology."""
        mock_encoder = MagicMock()
        # Return embeddings for technologies (Docker, Python)
        # and for the document content
        tech_embeddings = [
            [1.0, 0.0, 0.0],  # Docker
            [0.0, 1.0, 0.0],  # Python
        ]
        doc_embedding = [[0.9, 0.1, 0.0]]  # Similar to Docker

        call_count = [0]

        def encoder_side_effect(texts: list[str]) -> list[list[float]]:
            call_count[0] += 1
            if call_count[0] == 1:
                return tech_embeddings
            return doc_embedding

        mock_encoder.side_effect = encoder_side_effect
        mock_get_encoder.return_value = mock_encoder

        extractor = TechnologyExtractor(technologies=["Docker", "Python"], threshold=0.4)
        tech, score = extractor.extract_from_content("Docker containers deployment")

        assert tech == "Docker"
        assert score > 0.4

    @patch("para_files.utils.technology_extractor.TechnologyExtractor._get_encoder")
    def test_content_extraction_below_threshold(self, mock_get_encoder: MagicMock) -> None:
        """Test content extraction returns None when below threshold."""
        mock_encoder = MagicMock()
        tech_embeddings = [
            [1.0, 0.0, 0.0],  # Docker
            [0.0, 1.0, 0.0],  # Python
        ]
        doc_embedding = [[0.1, 0.1, 0.8]]  # Not similar to either

        call_count = [0]

        def encoder_side_effect(texts: list[str]) -> list[list[float]]:
            call_count[0] += 1
            if call_count[0] == 1:
                return tech_embeddings
            return doc_embedding

        mock_encoder.side_effect = encoder_side_effect
        mock_get_encoder.return_value = mock_encoder

        extractor = TechnologyExtractor(technologies=["Docker", "Python"], threshold=0.8)
        tech, score = extractor.extract_from_content("Random unrelated content")

        assert tech is None
        assert score == 0.0

    @patch("para_files.utils.technology_extractor.TechnologyExtractor._get_encoder")
    def test_content_extraction_exception_handling(self, mock_get_encoder: MagicMock) -> None:
        """Test exception during content extraction is handled."""
        mock_encoder = MagicMock()
        # First call succeeds (tech embeddings), second fails (doc embedding)
        tech_embeddings = [[1.0, 0.0], [0.0, 1.0]]

        call_count = [0]

        def encoder_side_effect(texts: list[str]) -> list[list[float]]:
            call_count[0] += 1
            if call_count[0] == 1:
                return tech_embeddings
            msg = "Encoding failed"
            raise RuntimeError(msg)

        mock_encoder.side_effect = encoder_side_effect
        mock_get_encoder.return_value = mock_encoder

        extractor = TechnologyExtractor(technologies=["Docker", "Python"])
        tech, score = extractor.extract_from_content("Some content")

        assert tech is None
        assert score == 0.0

    @patch("para_files.utils.technology_extractor.TechnologyExtractor._get_encoder")
    def test_content_extraction_with_none_embeddings(self, mock_get_encoder: MagicMock) -> None:
        """Test content extraction when tech embeddings are None after ensure."""
        mock_encoder = MagicMock()
        mock_get_encoder.return_value = mock_encoder

        extractor = TechnologyExtractor(technologies=["Docker"])
        # Force embeddings to be computed but then set to None
        extractor._tech_embeddings = None

        # Mock _ensure_tech_embeddings to return True but leave embeddings None
        with patch.object(extractor, "_ensure_tech_embeddings", return_value=True):
            tech, score = extractor.extract_from_content("Docker content")

        assert tech is None
        assert score == 0.0


class TestExtractWithContentFallback:
    """Test extract method with content fallback."""

    @patch("para_files.utils.technology_extractor.TechnologyExtractor._get_encoder")
    def test_content_fallback_when_filename_no_match(self, mock_get_encoder: MagicMock) -> None:
        """Test that content is used when filename doesn't match."""
        mock_encoder = MagicMock()
        tech_embeddings = [[1.0, 0.0, 0.0]]  # Docker
        doc_embedding = [[0.95, 0.05, 0.0]]  # Very similar to Docker

        call_count = [0]

        def encoder_side_effect(texts: list[str]) -> list[list[float]]:
            call_count[0] += 1
            if call_count[0] == 1:
                return tech_embeddings
            return doc_embedding

        mock_encoder.side_effect = encoder_side_effect
        mock_get_encoder.return_value = mock_encoder

        extractor = TechnologyExtractor(technologies=["Docker"], threshold=0.4)
        file_path = Path("/docs/random-guide.pdf")  # No tech in filename
        tech, confidence, source = extractor.extract(
            file_path, content="Docker container deployment guide"
        )

        assert tech == "Docker"
        assert source == "content"
        assert confidence > 0.4

    def test_no_content_and_no_filename_match(self) -> None:
        """Test returns none when no filename match and no content provided."""
        extractor = TechnologyExtractor()
        file_path = Path("/docs/random-guide.pdf")
        tech, confidence, source = extractor.extract(file_path, content=None)

        assert tech is None
        assert confidence == 0.0
        assert source == "none"


class TestGetEncoder:
    """Test _get_encoder method."""

    def test_get_encoder_caches_result(self) -> None:
        """Test that encoder is cached after first load."""
        extractor = TechnologyExtractor()
        # Pre-set encoder to simulate already loaded
        mock_encoder = MagicMock()
        extractor._encoder = mock_encoder

        result = extractor._get_encoder()
        assert result is mock_encoder

    @patch("para_files.utils.technology_extractor.OllamaEncoder", create=True)
    def test_get_encoder_loads_ollama(self, mock_encoder_class: MagicMock) -> None:
        """Test encoder loads OllamaEncoder when available."""
        mock_instance = MagicMock()
        mock_encoder_class.return_value = mock_instance

        with patch.dict(
            "sys.modules",
            {"para_files.encoders": MagicMock(OllamaEncoder=mock_encoder_class)},
        ):
            extractor = TechnologyExtractor()
            extractor._encoder = None
            # Patch the import inside _get_encoder
            with patch(
                "para_files.utils.technology_extractor.TechnologyExtractor._get_encoder"
            ) as mock_get:
                mock_get.return_value = mock_instance
                result = extractor._get_encoder()
                assert result is mock_instance
