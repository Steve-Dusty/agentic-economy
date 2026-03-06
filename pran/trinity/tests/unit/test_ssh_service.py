"""
Unit tests for async SSH service.

Tests the async methods for SSH credential management that use
Docker exec operations via the async docker_utils wrappers.

Module: src/backend/services/ssh_service.py
Issue: https://github.com/abilityai/trinity/issues/42
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import sys
import json
import importlib.util

# Add backend path for imports
backend_path = '/Users/eugene/Dropbox/trinity/trinity/src/backend'
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Mock crypt module (removed in Python 3.13+) - needs to be global
# as it's imported at runtime inside set_container_password()
if 'crypt' not in sys.modules:
    mock_crypt_global = Mock()
    mock_crypt_global.METHOD_SHA512 = "$6$"
    mock_crypt_global.mksalt = Mock(return_value="$6$random_salt$")
    mock_crypt_global.crypt = Mock(return_value="$6$random_salt$hashed_password")
    sys.modules['crypt'] = mock_crypt_global


def get_ssh_service():
    """Import SshService with mocked dependencies."""
    # Create mock modules to break the import chain
    mock_redis = Mock()
    mock_redis_client = Mock()
    mock_redis.from_url = Mock(return_value=mock_redis_client)

    mock_container = Mock()
    mock_get_agent_container = Mock(return_value=mock_container)
    mock_container_exec_run = AsyncMock()

    # Create mock for docker_utils
    mock_docker_utils = Mock()
    mock_docker_utils.container_exec_run = mock_container_exec_run

    # Create mock cryptography module structure
    mock_serialization = Mock()
    mock_serialization.Encoding = Mock()
    mock_serialization.Encoding.PEM = "PEM"
    mock_serialization.Encoding.OpenSSH = "OpenSSH"
    mock_serialization.PrivateFormat = Mock()
    mock_serialization.PrivateFormat.OpenSSH = "OpenSSH"
    mock_serialization.PublicFormat = Mock()
    mock_serialization.PublicFormat.OpenSSH = "OpenSSH"
    mock_serialization.NoEncryption = Mock(return_value=None)

    mock_ed25519 = Mock()
    mock_private_key = Mock()
    mock_public_key = Mock()
    mock_private_key.public_key = Mock(return_value=mock_public_key)
    mock_private_key.private_bytes = Mock(return_value=b"-----BEGIN OPENSSH PRIVATE KEY-----\ntest\n-----END OPENSSH PRIVATE KEY-----")
    mock_public_key.public_bytes = Mock(return_value=b"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAtest")
    mock_ed25519.Ed25519PrivateKey = Mock()
    mock_ed25519.Ed25519PrivateKey.generate = Mock(return_value=mock_private_key)

    mock_primitives = Mock()
    mock_primitives.serialization = mock_serialization
    mock_primitives.asymmetric = Mock()
    mock_primitives.asymmetric.ed25519 = mock_ed25519

    mock_hazmat = Mock()
    mock_hazmat.primitives = mock_primitives
    mock_hazmat.primitives.serialization = mock_serialization
    mock_hazmat.primitives.asymmetric = Mock()
    mock_hazmat.primitives.asymmetric.ed25519 = mock_ed25519

    mock_cryptography = Mock()
    mock_cryptography.hazmat = mock_hazmat
    mock_cryptography.hazmat.primitives = mock_primitives
    mock_cryptography.hazmat.primitives.serialization = mock_serialization
    mock_cryptography.hazmat.primitives.asymmetric = Mock()
    mock_cryptography.hazmat.primitives.asymmetric.ed25519 = mock_ed25519

    # Create mock crypt module (removed in Python 3.13+)
    mock_crypt = Mock()
    mock_crypt.METHOD_SHA512 = "$6$"
    mock_crypt.mksalt = Mock(return_value="$6$random_salt$")
    mock_crypt.crypt = Mock(return_value="$6$random_salt$hashed_password")

    # Pre-populate sys.modules with mocks
    with patch.dict('sys.modules', {
        'redis': mock_redis,
        'crypt': mock_crypt,
        'cryptography': mock_cryptography,
        'cryptography.hazmat': mock_hazmat,
        'cryptography.hazmat.primitives': mock_primitives,
        'cryptography.hazmat.primitives.serialization': mock_serialization,
        'cryptography.hazmat.primitives.asymmetric': Mock(ed25519=mock_ed25519),
        'cryptography.hazmat.primitives.asymmetric.ed25519': mock_ed25519,
        'services.docker_service': Mock(get_agent_container=mock_get_agent_container),
        'services.docker_utils': mock_docker_utils,
    }):
        # Force reimport
        if 'services.ssh_service' in sys.modules:
            del sys.modules['services.ssh_service']

        # Load module directly
        spec = importlib.util.spec_from_file_location(
            "ssh_service",
            f"{backend_path}/services/ssh_service.py"
        )
        ssh_service = importlib.util.module_from_spec(spec)

        # Inject mocks
        ssh_service.redis = mock_redis
        ssh_service.get_agent_container = mock_get_agent_container
        ssh_service.container_exec_run = mock_container_exec_run

        spec.loader.exec_module(ssh_service)

        return ssh_service, {
            'redis': mock_redis,
            'redis_client': mock_redis_client,
            'get_agent_container': mock_get_agent_container,
            'container_exec_run': mock_container_exec_run,
            'container': mock_container,
            'mock_private_key': mock_private_key,
            'mock_public_key': mock_public_key,
        }


@pytest.mark.unit
class TestSshKeyGeneration:
    """Test SSH key pair generation (synchronous, no Docker)."""

    def test_generate_ssh_keypair_returns_valid_keys(self):
        """generate_ssh_keypair() returns private key, public key, and comment."""
        ssh_service, mocks = get_ssh_service()
        service = ssh_service.SshService()

        keypair = service.generate_ssh_keypair("test-agent")

        assert "private_key" in keypair
        assert "public_key" in keypair
        assert "comment" in keypair

        # Verify the mocked key format is present
        assert "-----BEGIN OPENSSH PRIVATE KEY-----" in keypair["private_key"]
        assert "ssh-ed25519" in keypair["public_key"]
        # Comment should contain agent name
        assert "test-agent" in keypair["comment"]

    def test_generate_password_returns_secure_string(self):
        """generate_password() returns alphanumeric password of correct length."""
        ssh_service, mocks = get_ssh_service()
        service = ssh_service.SshService()

        password = service.generate_password(length=24)

        assert len(password) == 24
        assert password.isalnum()

    def test_generate_password_different_each_time(self):
        """generate_password() returns unique passwords."""
        ssh_service, mocks = get_ssh_service()
        service = ssh_service.SshService()

        passwords = [service.generate_password() for _ in range(10)]

        # All passwords should be unique
        assert len(set(passwords)) == 10


@pytest.mark.unit
class TestAsyncSshKeyInjection:
    """Test async SSH key injection into containers."""

    @pytest.mark.asyncio
    async def test_inject_ssh_key_uses_async_exec(self):
        """inject_ssh_key() uses async container_exec_run()."""
        ssh_service, mocks = get_ssh_service()
        service = ssh_service.SshService()

        mock_container = Mock()
        mock_exec_result = Mock()
        mock_exec_result.exit_code = 0
        mock_exec_result.output = b""

        mocks['get_agent_container'].return_value = mock_container
        mocks['container_exec_run'].return_value = mock_exec_result

        result = await service.inject_ssh_key(
            "test-agent",
            "ssh-ed25519 AAAA... trinity-ephemeral-test"
        )

        assert result is True
        # Should call exec 3 times: mkdir, append key, chmod
        assert mocks['container_exec_run'].call_count == 3

    @pytest.mark.asyncio
    async def test_inject_ssh_key_returns_false_on_container_not_found(self):
        """inject_ssh_key() returns False when container doesn't exist."""
        ssh_service, mocks = get_ssh_service()
        service = ssh_service.SshService()

        mocks['get_agent_container'].return_value = None

        result = await service.inject_ssh_key("nonexistent-agent", "ssh-ed25519 AAAA...")

        assert result is False

    @pytest.mark.asyncio
    async def test_inject_ssh_key_returns_false_on_exec_failure(self):
        """inject_ssh_key() returns False when exec command fails."""
        ssh_service, mocks = get_ssh_service()
        service = ssh_service.SshService()

        mock_container = Mock()
        mocks['get_agent_container'].return_value = mock_container

        # First call succeeds (mkdir), second fails (append key)
        mock_success = Mock(exit_code=0, output=b"")
        mock_failure = Mock(exit_code=1, output=b"Permission denied")
        mocks['container_exec_run'].side_effect = [mock_success, mock_failure]

        result = await service.inject_ssh_key("test-agent", "ssh-ed25519 AAAA...")

        assert result is False


@pytest.mark.unit
class TestAsyncPasswordManagement:
    """Test async password setting/clearing in containers."""

    @pytest.mark.asyncio
    async def test_set_container_password_uses_async_exec(self):
        """set_container_password() uses async container_exec_run()."""
        ssh_service, mocks = get_ssh_service()
        service = ssh_service.SshService()

        mock_container = Mock()
        mock_exec_result = Mock()
        mock_exec_result.exit_code = 0
        mock_exec_result.output = b""

        mocks['get_agent_container'].return_value = mock_container
        mocks['container_exec_run'].return_value = mock_exec_result

        result = await service.set_container_password("test-agent", "securepass123")

        assert result is True
        # Should call exec multiple times: usermod, sed, pkill, sshd
        assert mocks['container_exec_run'].call_count >= 3

    @pytest.mark.asyncio
    async def test_clear_container_password_uses_async_exec(self):
        """clear_container_password() uses async container_exec_run()."""
        ssh_service, mocks = get_ssh_service()
        service = ssh_service.SshService()

        mock_container = Mock()
        mock_exec_result = Mock()
        mock_exec_result.exit_code = 0
        mock_exec_result.output = b""

        mocks['get_agent_container'].return_value = mock_container
        mocks['container_exec_run'].return_value = mock_exec_result

        result = await service.clear_container_password("test-agent")

        assert result is True
        mocks['container_exec_run'].assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_container_password_returns_true_when_container_missing(self):
        """clear_container_password() returns True when container doesn't exist (cleanup ok)."""
        ssh_service, mocks = get_ssh_service()
        service = ssh_service.SshService()

        mocks['get_agent_container'].return_value = None

        result = await service.clear_container_password("deleted-agent")

        # Should return True because container deletion means credential cleanup succeeded
        assert result is True


@pytest.mark.unit
class TestAsyncKeyRemoval:
    """Test async SSH key removal from containers."""

    @pytest.mark.asyncio
    async def test_remove_ssh_key_uses_async_exec(self):
        """remove_ssh_key() uses async container_exec_run()."""
        ssh_service, mocks = get_ssh_service()
        service = ssh_service.SshService()

        mock_container = Mock()
        mock_exec_result = Mock()
        mock_exec_result.exit_code = 0
        mock_exec_result.output = b""

        mocks['get_agent_container'].return_value = mock_container
        mocks['container_exec_run'].return_value = mock_exec_result

        result = await service.remove_ssh_key(
            "test-agent",
            "trinity-ephemeral-test-agent-1234567890"
        )

        assert result is True
        mocks['container_exec_run'].assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_ssh_key_returns_true_when_container_missing(self):
        """remove_ssh_key() returns True when container doesn't exist (cleanup ok)."""
        ssh_service, mocks = get_ssh_service()
        service = ssh_service.SshService()

        mocks['get_agent_container'].return_value = None

        result = await service.remove_ssh_key("deleted-agent", "key-comment")

        assert result is True


@pytest.mark.unit
class TestAsyncCleanupOperations:
    """Test async credential cleanup operations."""

    @pytest.mark.asyncio
    async def test_cleanup_agent_credentials_removes_keys_and_passwords(self):
        """cleanup_agent_credentials() removes all credentials for an agent."""
        ssh_service, mocks = get_ssh_service()

        # Configure Redis mock
        mocks['redis_client'].keys.return_value = [
            "ssh_access:test-agent:key1",
            "ssh_access:test-agent:pwd1"
        ]
        mocks['redis_client'].get.side_effect = [
            json.dumps({"auth_type": "key", "credential_id": "key1"}),
            json.dumps({"auth_type": "password", "credential_id": "pwd1"})
        ]

        service = ssh_service.SshService()

        mock_container = Mock()
        mock_exec_result = Mock()
        mock_exec_result.exit_code = 0
        mock_exec_result.output = b""

        mocks['get_agent_container'].return_value = mock_container
        mocks['container_exec_run'].return_value = mock_exec_result

        count = await service.cleanup_agent_credentials("test-agent")

        assert count == 2
        # Should delete Redis keys
        assert mocks['redis_client'].delete.call_count == 2

    @pytest.mark.asyncio
    async def test_revoke_key_removes_from_container_and_redis(self):
        """revoke_key() removes key from container and Redis."""
        ssh_service, mocks = get_ssh_service()
        service = ssh_service.SshService()

        mock_container = Mock()
        mock_exec_result = Mock()
        mock_exec_result.exit_code = 0
        mock_exec_result.output = b""

        mocks['get_agent_container'].return_value = mock_container
        mocks['container_exec_run'].return_value = mock_exec_result

        result = await service.revoke_key("test-agent", "key-comment")

        assert result is True
        mocks['redis_client'].delete.assert_called_once_with(
            "ssh_access:test-agent:key-comment"
        )


@pytest.mark.unit
class TestRedisMetadataStorage:
    """Test Redis metadata storage (synchronous)."""

    def test_store_credential_metadata_sets_redis_key_with_ttl(self):
        """store_credential_metadata() stores JSON with TTL in Redis."""
        ssh_service, mocks = get_ssh_service()
        service = ssh_service.SshService()

        service.store_credential_metadata(
            agent_name="test-agent",
            credential_id="key-123",
            auth_type="key",
            created_by="admin@example.com",
            ttl_hours=4.0,
            public_key="ssh-ed25519 AAAA..."
        )

        mocks['redis_client'].setex.assert_called_once()
        call_args = mocks['redis_client'].setex.call_args

        # Verify key format
        assert call_args[0][0] == "ssh_access:test-agent:key-123"

        # Verify TTL (4 hours = 14400 seconds)
        assert call_args[0][1] == 14400

        # Verify JSON content
        stored_data = json.loads(call_args[0][2])
        assert stored_data["agent_name"] == "test-agent"
        assert stored_data["auth_type"] == "key"
        assert stored_data["public_key"] == "ssh-ed25519 AAAA..."

    def test_list_active_keys_returns_all_credentials(self):
        """list_active_keys() returns all active credentials from Redis."""
        ssh_service, mocks = get_ssh_service()

        mocks['redis_client'].keys.return_value = [
            "ssh_access:agent1:key1",
            "ssh_access:agent2:key2"
        ]
        mocks['redis_client'].get.side_effect = [
            json.dumps({"agent_name": "agent1", "auth_type": "key"}),
            json.dumps({"agent_name": "agent2", "auth_type": "password"})
        ]

        service = ssh_service.SshService()
        keys = service.list_active_keys()

        assert len(keys) == 2
        assert keys[0]["agent_name"] == "agent1"
        assert keys[1]["agent_name"] == "agent2"
