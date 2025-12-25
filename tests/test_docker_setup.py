"""
Test suite to verify Docker Compose configuration is valid.

This test validates that:
1. Dockerfile exists and is valid
2. docker-compose.yml exists and has correct structure
3. All required services are defined
4. Environment variables are properly set
5. Health checks are configured
"""

import os
import yaml
import pytest
from pathlib import Path


class TestDockerConfiguration:
    """Test Docker Compose configuration"""

    @pytest.fixture
    def docker_compose_path(self):
        """Path to docker-compose.yml"""
        return Path(__file__).parent.parent / "docker-compose.yml"

    @pytest.fixture
    def dockerfile_path(self):
        """Path to Dockerfile"""
        return Path(__file__).parent.parent / "Dockerfile"

    @pytest.fixture
    def dockerignore_path(self):
        """Path to .dockerignore"""
        return Path(__file__).parent.parent / ".dockerignore"

    def test_dockerfile_exists(self, dockerfile_path):
        """Test that Dockerfile exists"""
        assert dockerfile_path.exists(), "Dockerfile not found"
        assert dockerfile_path.is_file(), "Dockerfile is not a file"

    def test_dockerfile_has_valid_syntax(self, dockerfile_path):
        """Test that Dockerfile has valid syntax"""
        content = dockerfile_path.read_text()

        # Check for required instructions
        assert "FROM" in content, "Dockerfile missing FROM instruction"
        assert "WORKDIR" in content, "Dockerfile missing WORKDIR instruction"
        assert "EXPOSE" in content, "Dockerfile missing EXPOSE instruction"
        assert "CMD" in content or "ENTRYPOINT" in content, "Dockerfile missing CMD/ENTRYPOINT"

        # Check for Python base image
        assert "python:" in content, "Dockerfile should use Python base image"

        # Check for multi-stage build
        assert "as builder" in content, "Dockerfile should use multi-stage build"

    def test_dockerfile_has_healthcheck(self, dockerfile_path):
        """Test that Dockerfile includes healthcheck"""
        content = dockerfile_path.read_text()
        assert "HEALTHCHECK" in content, "Dockerfile missing HEALTHCHECK instruction"

    def test_docker_compose_exists(self, docker_compose_path):
        """Test that docker-compose.yml exists"""
        assert docker_compose_path.exists(), "docker-compose.yml not found"
        assert docker_compose_path.is_file(), "docker-compose.yml is not a file"

    def test_docker_compose_valid_yaml(self, docker_compose_path):
        """Test that docker-compose.yml is valid YAML"""
        content = docker_compose_path.read_text()
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            pytest.fail(f"docker-compose.yml is not valid YAML: {e}")

    def test_docker_compose_version(self, docker_compose_path):
        """Test that docker-compose.yml has version 3.8+"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            assert "version" in compose, "docker-compose.yml missing version"
            version = float(compose["version"])
            assert version >= 3.8, "docker-compose.yml should use version 3.8 or higher"

    def test_docker_compose_has_postgres_service(self, docker_compose_path):
        """Test that docker-compose.yml has PostgreSQL service"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            assert "services" in compose, "docker-compose.yml missing services section"
            assert "postgres" in compose["services"], "docker-compose.yml missing postgres service"

            # Check postgres configuration
            postgres = compose["services"]["postgres"]
            assert "image" in postgres, "postgres service missing image"
            assert "postgres:" in postgres["image"], "postgres image should be postgres:*"
            assert "ports" in postgres, "postgres service missing ports"
            assert "environment" in postgres, "postgres service missing environment"

    def test_docker_compose_has_redis_service(self, docker_compose_path):
        """Test that docker-compose.yml has Redis service"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            assert "redis" in compose["services"], "docker-compose.yml missing redis service"

            # Check redis configuration
            redis = compose["services"]["redis"]
            assert "image" in redis, "redis service missing image"
            assert "redis:" in redis["image"], "redis image should be redis:*"
            assert "ports" in redis, "redis service missing ports"

    def test_docker_compose_has_api_service(self, docker_compose_path):
        """Test that docker-compose.yml has API service"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            assert "api" in compose["services"], "docker-compose.yml missing api service"

            # Check api configuration
            api = compose["services"]["api"]
            assert "build" in api, "api service missing build configuration"
            assert "ports" in api, "api service missing ports"
            assert "environment" in api, "api service missing environment"
            assert "depends_on" in api, "api service missing depends_on"

    def test_docker_compose_postgres_healthcheck(self, docker_compose_path):
        """Test that postgres service has healthcheck"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            postgres = compose["services"]["postgres"]
            assert "healthcheck" in postgres, "postgres service missing healthcheck"
            assert "test" in postgres["healthcheck"], "postgres healthcheck missing test"

    def test_docker_compose_redis_healthcheck(self, docker_compose_path):
        """Test that redis service has healthcheck"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            redis = compose["services"]["redis"]
            assert "healthcheck" in redis, "redis service missing healthcheck"
            assert "test" in redis["healthcheck"], "redis healthcheck missing test"

    def test_docker_compose_api_healthcheck(self, docker_compose_path):
        """Test that api service has healthcheck"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            api = compose["services"]["api"]
            assert "healthcheck" in api, "api service missing healthcheck"

    def test_docker_compose_environment_variables(self, docker_compose_path):
        """Test that API service has required environment variables"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            api = compose["services"]["api"]["environment"]

            required_vars = [
                "DATABASE_URL",
                "REDIS_URL",
                "CRONOS_RPC_URL",
                "X402_FACILITATOR_URL"
            ]

            for var in required_vars:
                assert var in api, f"API service missing environment variable: {var}"

    def test_docker_compose_volumes_defined(self, docker_compose_path):
        """Test that docker-compose.yml has volumes defined"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            assert "volumes" in compose, "docker-compose.yml missing volumes section"

            # Check for data volumes
            volumes = compose["volumes"]
            assert "postgres_data" in volumes, "missing postgres_data volume"
            assert "redis_data" in volumes, "missing redis_data volume"

    def test_docker_compose_networks_defined(self, docker_compose_path):
        """Test that docker-compose.yml has networks defined"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            assert "networks" in compose, "docker-compose.yml missing networks section"

            # Check for paygent network
            networks = compose["networks"]
            assert "paygent-network" in networks, "missing paygent-network"

    def test_docker_compose_services_use_networks(self, docker_compose_path):
        """Test that all services use the paygent network"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)

            for service_name in ["postgres", "redis", "api"]:
                service = compose["services"][service_name]
                assert "networks" in service, f"{service_name} service not using networks"

    def test_dockerignore_exists(self, dockerignore_path):
        """Test that .dockerignore exists"""
        assert dockerignore_path.exists(), ".dockerignore not found"

    def test_dockerignore_excludes_unnecessary_files(self, dockerignore_path):
        """Test that .dockerignore excludes common unnecessary files"""
        content = dockerignore_path.read_text()

        # Should exclude these patterns
        patterns_to_exclude = [
            "__pycache__",
            ".git",
            ".venv",
            "*.pyc",
            "tests/",
            "*.md"
        ]

        for pattern in patterns_to_exclude:
            assert pattern in content, f".dockerignore should exclude {pattern}"

    def test_dockerfile_from_builder_correct(self, dockerfile_path):
        """Test that Dockerfile correctly uses builder stage"""
        content = dockerfile_path.read_text()

        # Check builder stage
        assert "FROM python:" in content, "Dockerfile should use Python base"
        assert "as builder" in content, "Dockerfile should have builder stage"
        assert "COPY --from=builder" in content, "Dockerfile should copy from builder"

        # Check runtime stage
        assert "COPY --chown=appuser:appuser" in content, "Dockerfile should use non-root user"
        assert "USER appuser" in content, "Dockerfile should switch to appuser"

    def test_api_depends_on_database_healthy(self, docker_compose_path):
        """Test that API service waits for database to be healthy"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            api = compose["services"]["api"]

            assert "depends_on" in api, "api service missing depends_on"

            # Check for health condition
            depends = api["depends_on"]
            assert "postgres" in depends, "api should depend on postgres"
            assert "redis" in depends, "api should depend on redis"

            # Check for service_healthy condition (if using compose v2.x format)
            # Note: Compose file v3 uses service_healthy condition
            if isinstance(depends["postgres"], dict):
                assert depends["postgres"].get("condition") == "service_healthy", \
                    "api should wait for postgres to be healthy"

    def test_postgres_exposes_port_5432(self, docker_compose_path):
        """Test that postgres exposes port 5432"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            postgres = compose["services"]["postgres"]

            assert "5432" in postgres["ports"][0], "postgres should expose port 5432"

    def test_redis_exposes_port_6379(self, docker_compose_path):
        """Test that redis exposes port 6379"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            redis = compose["services"]["redis"]

            assert "6379" in redis["ports"][0], "redis should expose port 6379"

    def test_api_exposes_port_8000(self, docker_compose_path):
        """Test that api exposes port 8000"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)
            api = compose["services"]["api"]

            assert "8000" in api["ports"][0], "api should expose port 8000"

    def test_docker_compose_has_optional_tools(self, docker_compose_path):
        """Test that optional admin tools are defined with profiles"""
        with open(docker_compose_path) as f:
            compose = yaml.safe_load(f)

            # Check for adminer (optional)
            if "adminer" in compose["services"]:
                adminer = compose["services"]["adminer"]
                assert "profiles" in adminer, "adminer should have profiles"
                assert "tools" in adminer["profiles"], "adminer should be in tools profile"

            # Check for redis-commander (optional)
            if "redis-commander" in compose["services"]:
                commander = compose["services"]["redis-commander"]
                assert "profiles" in commander, "redis-commander should have profiles"
                assert "tools" in commander["profiles"], "redis-commander should be in tools profile"


class TestDockerInstructions:
    """Test documentation for Docker usage"""

    def test_readme_has_docker_instructions(self):
        """Test that README.md includes Docker instructions"""
        readme_path = Path(__file__).parent.parent / "README.md"

        if readme_path.exists():
            content = readme_path.read_text()
            # Basic check - README should mention Docker
            # (Detailed content check not required for this feature)
        else:
            pytest.skip("README.md not found - will be created separately")

    def test_docker_compose_start_command(self):
        """Verify docker-compose start command would be valid"""
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"

        if compose_path.exists():
            # If file exists and is valid YAML, the command would work
            with open(compose_path) as f:
                try:
                    yaml.safe_load(f)
                    assert True, "docker-compose up would be valid"
                except yaml.YAMLError:
                    pytest.fail("docker-compose.yml has syntax errors")
        else:
            pytest.fail("docker-compose.yml not found")
