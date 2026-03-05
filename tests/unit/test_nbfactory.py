"""Unit tests for NBFactory class."""

import sys
from unittest.mock import Mock, MagicMock, patch

# Mock pynetbox exceptions before importing nrx
mock_pynetbox_module = MagicMock()
mock_pynetbox_module.core.query.RequestError = Exception
mock_pynetbox_module.core.query.ContentError = Exception
sys.modules['pynetbox'] = mock_pynetbox_module
sys.modules['pynetbox.core'] = mock_pynetbox_module.core
sys.modules['pynetbox.core.query'] = mock_pynetbox_module.core.query

from nrx.nrx import NBFactory  # pylint: disable=wrong-import-position


def make_mock_device_dict_compatible(mock_device, device_dict):
    """Helper to make a mock device compatible with dict() conversion."""
    # Mock wraps magic methods and passes the mock instance as first arg,
    # so these callables must accept a dummy `self` parameter.
    def get_keys():
        return device_dict.keys()

    def get_item(_, key):
        return device_dict[key]

    def get_iter(_):
        return iter(device_dict)

    mock_device.keys = get_keys
    mock_device.__getitem__ = get_item
    mock_device.__iter__ = get_iter


def create_test_config():
    """Create a minimal test configuration."""
    return {
        'nb_api_url': 'https://netbox.example.com',
        'nb_api_token': 'test_token',
        'tls_validate': True,
        'api_timeout': 10,
        'export_sites': [],
        'export_tags': ['test-tag'],
        'export_device_roles': ['router'],
        'topology_name': '',
        'export_configs': False,
        'export_links': True,
        'nb_api_params': {
            'interfaces_block_size': 4,
            'cables_block_size': 64,
        }
    }


def setup_mock_api(mock_pynetbox, api_version="4.0.0"):
    """Setup mock pynetbox API."""
    mock_api = Mock()
    mock_api.version = api_version
    mock_pynetbox.api.return_value = mock_api
    # Mock empty returns to avoid actual API calls
    mock_api.dcim.devices.filter.return_value = []
    mock_api.dcim.interfaces.filter.return_value = []
    mock_api.dcim.cables.filter.return_value = []
    return mock_api


class TestNBFactoryInitialization:
    """Test NBFactory initialization."""

    @patch('nrx.nrx.pynetbox')
    def test_nb_sites_initialized_as_list(self, mock_pynetbox):
        """Test that nb_sites is initialized as an empty list, not None."""
        # Mock the pynetbox API
        mock_api = Mock()
        mock_api.version = "3.5.0"
        mock_pynetbox.api.return_value = mock_api
        # Mock the exception classes
        mock_pynetbox.core.query.RequestError = Exception
        mock_pynetbox.core.query.ContentError = Exception

        # Create minimal config
        config = {
            'nb_api_url': 'https://netbox.example.com',
            'nb_api_token': 'test_token',
            'tls_validate': True,
            'api_timeout': 10,
            'export_sites': [],
            'export_tags': ['test-tag'],
            'export_device_roles': ['router'],
            'topology_name': '',
            'export_configs': False,
            'export_links': True,
            'nb_api_params': {
                'interfaces_block_size': 4,
                'cables_block_size': 64,
            }
        }

        # Mock device filter to return empty list to avoid actual API calls
        mock_api.dcim.devices.filter.return_value = []
        mock_api.dcim.interfaces.filter.return_value = []
        mock_api.dcim.cables.filter.return_value = []

        # Create NBFactory instance
        nb_factory = NBFactory(config)

        # Verify nb_sites is initialized as list, not None
        assert nb_factory.nb_sites == []
        assert isinstance(nb_factory.nb_sites, list)
        assert nb_factory.nb_sites is not None


class TestNBSitesInitialization:
    """Test nb_sites initialization and usage."""

    @patch('nrx.nrx.pynetbox')
    def test_len_on_nb_sites_works(self, mock_pynetbox):
        """Test that len(self.nb_sites) works without TypeError."""
        # Mock the pynetbox API
        mock_api = Mock()
        mock_api.version = "3.5.0"
        mock_pynetbox.api.return_value = mock_api
        # Mock the exception classes
        mock_pynetbox.core.query.RequestError = Exception
        mock_pynetbox.core.query.ContentError = Exception

        # Create config
        config = {
            'nb_api_url': 'https://netbox.example.com',
            'nb_api_token': 'test_token',
            'tls_validate': True,
            'api_timeout': 10,
            'export_sites': [],
            'export_tags': ['test-tag'],
            'export_device_roles': ['router'],
            'topology_name': '',
            'export_configs': False,
            'export_links': True,
            'nb_api_params': {
                'interfaces_block_size': 4,
                'cables_block_size': 64,
            }
        }

        # Mock empty returns
        mock_api.dcim.devices.filter.return_value = []
        mock_api.dcim.interfaces.filter.return_value = []
        mock_api.dcim.cables.filter.return_value = []

        # Create NBFactory instance
        nb_factory = NBFactory(config)

        # This should not raise TypeError
        assert len(nb_factory.nb_sites) == 0
        # Verify it's a list
        assert isinstance(nb_factory.nb_sites, list)


class TestInitDevice:
    """Test _init_device method behavior."""

    @patch('nrx.nrx.pynetbox')
    def test_init_device_preserves_all_raw_fields(self, mock_pynetbox):  # pylint: disable=too-many-statements
        """Test that _init_device preserves all raw NetBox device fields."""
        setup_mock_api(mock_pynetbox)
        nb_factory = NBFactory(create_test_config())

        # Create a mock device with raw NetBox fields
        mock_device = Mock()
        mock_device.id = 123
        mock_device.name = "test-device"
        mock_device.serial = "ABC123456"
        mock_device.asset_tag = "ASSET-001"
        mock_device.comments = "Test device comments"
        mock_device.status = Mock(value="active", label="Active")
        mock_device.custom_fields = {"environment": "production", "owner": "team-a"}
        mock_device.tags = [Mock(name="tag1"), Mock(name="tag2")]

        # Mock nested objects
        mock_site = Mock()
        mock_site.id = 1
        mock_site.name = "Site 1"
        mock_site.slug = "site-1"
        mock_device.site = mock_site

        mock_platform = Mock()
        mock_platform.id = 2
        mock_platform.name = "Test Platform"
        mock_platform.slug = "test-platform"
        mock_device.platform = mock_platform

        mock_manufacturer = Mock()
        mock_manufacturer.id = 3
        mock_manufacturer.name = "Test Vendor"
        mock_manufacturer.slug = "test-vendor"

        mock_device_type = Mock()
        mock_device_type.id = 4
        mock_device_type.model = "Test Model"
        mock_device_type.slug = "test-model"
        mock_device_type.manufacturer = mock_manufacturer
        mock_device.device_type = mock_device_type

        mock_role = Mock()
        mock_role.id = 5
        mock_role.name = "Router"
        mock_role.slug = "router"
        mock_device.role = mock_role

        mock_device.primary_ip4 = Mock(id=6, address="10.0.0.1/24")
        mock_device.primary_ip6 = Mock(id=7, address="2001:db8::1/64")
        mock_device.tenant = None
        mock_device.location = None
        mock_device.rack = None

        # Mock dict() conversion
        device_dict = {
            'id': 123,
            'name': 'test-device',
            'serial': 'ABC123456',
            'asset_tag': 'ASSET-001',
            'comments': 'Test device comments',
            'custom_fields': {"environment": "production", "owner": "team-a"},
        }
        make_mock_device_dict_compatible(mock_device, device_dict)

        # Call _init_device
        result = nb_factory._init_device(mock_device)  # pylint: disable=protected-access

        # Verify raw NetBox fields are preserved
        assert result['id'] == 123
        assert result['name'] == 'test-device'
        assert result['serial'] == 'ABC123456'
        assert result['asset_tag'] == 'ASSET-001'
        assert result['comments'] == 'Test device comments'
        assert result['custom_fields'] == {"environment": "production", "owner": "team-a"}

    @patch('nrx.nrx.pynetbox')
    def test_init_device_backward_compatible_fields(self, mock_pynetbox):
        """Test that _init_device extracts backward-compatible fields correctly."""
        setup_mock_api(mock_pynetbox)
        nb_factory = NBFactory(create_test_config())

        # Create a mock device
        mock_device = Mock()
        mock_device.id = 123
        mock_device.name = "test-router"

        # Mock site
        mock_site = Mock()
        mock_site.name = "Site 1"
        mock_device.site = mock_site

        # Mock platform
        mock_platform = Mock()
        mock_platform.slug = "arista-eos"
        mock_platform.name = "Arista EOS"
        mock_device.platform = mock_platform

        # Mock device_type and manufacturer
        mock_manufacturer = Mock()
        mock_manufacturer.slug = "arista"
        mock_manufacturer.name = "Arista"

        mock_device_type = Mock()
        mock_device_type.slug = "dcs-7050sx-128"
        mock_device_type.model = "DCS-7050SX-128"
        mock_device_type.manufacturer = mock_manufacturer
        mock_device.device_type = mock_device_type

        # Mock role
        mock_role = Mock()
        mock_role.slug = "spine"
        mock_role.name = "Spine"
        mock_device.role = mock_role

        # Mock IPs
        mock_device.primary_ip4 = Mock(address="192.168.1.1/24")
        mock_device.primary_ip6 = Mock(address="fe80::1/64")

        mock_device.tenant = None
        mock_device.location = None
        mock_device.rack = None

        # Mock dict() conversion
        device_dict = {
            'id': 123,
            'name': 'test-router',
        }
        make_mock_device_dict_compatible(mock_device, device_dict)

        # Call _init_device
        result = nb_factory._init_device(mock_device)  # pylint: disable=protected-access

        # Verify backward-compatible fields
        assert result['type'] == 'device'
        assert result['node_id'] == -1
        assert result['name'] == 'test-router'
        assert result['site'] == 'Site 1'
        assert result['platform'] == 'arista-eos'
        assert result['platform_name'] == 'Arista EOS'
        assert result['model'] == 'dcs-7050sx-128'
        assert result['model_name'] == 'DCS-7050SX-128'
        assert result['vendor'] == 'arista'
        assert result['vendor_name'] == 'Arista'
        assert result['role'] == 'spine'
        assert result['role_name'] == 'Spine'
        assert result['primary_ip4'] == '192.168.1.1/24'
        assert result['primary_ip6'] == 'fe80::1/64'
        assert result['config'] == ''

    @patch('nrx.nrx.pynetbox')
    def test_init_device_handles_none_values(self, mock_pynetbox):
        """Test that _init_device handles None values correctly."""
        setup_mock_api(mock_pynetbox)
        nb_factory = NBFactory(create_test_config())

        # Create a mock device with None values
        mock_device = Mock()
        mock_device.id = 456
        mock_device.name = None
        mock_device.site = None
        mock_device.platform = None
        mock_device.device_type = None
        mock_role = Mock()
        mock_role.slug = "unknown"
        mock_role.name = "Unknown"
        mock_device.role = mock_role
        mock_device.primary_ip4 = None
        mock_device.primary_ip6 = None
        mock_device.tenant = None
        mock_device.location = None
        mock_device.rack = None

        # Mock dict() conversion
        device_dict = {
            'id': 456,
            'name': None,
        }
        make_mock_device_dict_compatible(mock_device, device_dict)

        # Call _init_device
        result = nb_factory._init_device(mock_device)  # pylint: disable=protected-access

        # Verify defaults for None values
        assert result['name'] == 'unknown-456'  # Auto-generated from role
        assert result['site'] == ''
        assert result['platform'] == 'unknown'
        assert result['platform_name'] == 'unknown'
        assert result['model'] == 'unknown'
        assert result['model_name'] == 'unknown'
        assert result['vendor'] == 'unknown'
        assert result['vendor_name'] == 'unknown'
        assert result['primary_ip4'] == ''
        assert result['primary_ip6'] == ''

    @patch('nrx.nrx.pynetbox')
    def test_init_device_netbox_v3_compatibility(self, mock_pynetbox):
        """Test that _init_device handles NetBox v3.x device_role correctly."""
        setup_mock_api(mock_pynetbox, api_version="3.7.0")
        nb_factory = NBFactory(create_test_config())

        # Create a mock device with NetBox v3.x style device_role
        mock_device = Mock()
        mock_device.id = 789
        mock_device.name = "v3-device"
        mock_device.site = None
        mock_device.platform = None
        mock_device.device_type = None
        mock_device.role = None  # v4 field not present
        mock_device_role = Mock()
        mock_device_role.slug = "leaf"
        mock_device_role.name = "Leaf"
        mock_device.device_role = mock_device_role  # v3 field
        mock_device.primary_ip4 = None
        mock_device.primary_ip6 = None
        mock_device.tenant = None
        mock_device.location = None
        mock_device.rack = None

        # Mock dict() conversion
        device_dict = {
            'id': 789,
            'name': 'v3-device',
        }
        make_mock_device_dict_compatible(mock_device, device_dict)

        # Call _init_device
        result = nb_factory._init_device(mock_device)  # pylint: disable=protected-access

        # Verify it uses device_role instead of role for v3.x
        assert result['role'] == 'leaf'
        assert result['role_name'] == 'Leaf'
