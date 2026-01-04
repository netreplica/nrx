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


class TestNBFactoryInitialization:
    """Test NBFactory initialization."""

    @patch('nrx.nrx.pynetbox')
    def test_nb_sites_initialized_as_list(self, mock_pynetbox):
        """Test that nb_sites is initialized as an empty list, not None."""
        # Mock the pynetbox API
        mock_api = Mock()
        mock_api.version = "3.5.0"
        mock_pynetbox.api.return_value = mock_api

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
