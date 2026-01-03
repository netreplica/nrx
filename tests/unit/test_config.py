"""Unit tests for configuration loading and backward compatibility."""

import os
import tempfile
import pytest
from nrx.nrx import load_toml_config


class TestConfigBackwardCompatibility:
    """Test backward compatibility for EXPORT_SITE config key."""

    def test_export_site_singular_string(self):
        """Test that EXPORT_SITE (singular, string) is converted to export_sites (plural, list)."""
        # Create a temporary config file with EXPORT_SITE (singular)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("EXPORT_SITE = 'Santa Clara'\n")
            f.write("EXPORT_TAGS = []\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)

            # Verify EXPORT_SITE was converted to export_sites list
            assert config['export_sites'] == ['Santa Clara']
            assert isinstance(config['export_sites'], list)
        finally:
            os.unlink(config_path)

    def test_export_sites_plural_list(self):
        """Test that EXPORT_SITES (plural, list) works correctly."""
        # Create a temporary config file with EXPORT_SITES (plural)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("EXPORT_SITES = ['Site1', 'Site2']\n")
            f.write("EXPORT_TAGS = []\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)

            # Verify EXPORT_SITES is loaded correctly
            assert config['export_sites'] == ['Site1', 'Site2']
            assert isinstance(config['export_sites'], list)
        finally:
            os.unlink(config_path)

    def test_export_site_list_backward_compat(self):
        """Test that EXPORT_SITE (singular) with list value is handled."""
        # Create a temporary config file with EXPORT_SITE as a list
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("EXPORT_SITE = ['Site1', 'Site2']\n")
            f.write("EXPORT_TAGS = []\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)

            # Verify EXPORT_SITE list is converted to export_sites
            assert config['export_sites'] == ['Site1', 'Site2']
            assert isinstance(config['export_sites'], list)
        finally:
            os.unlink(config_path)

    def test_export_sites_takes_precedence(self):
        """Test that EXPORT_SITES takes precedence over EXPORT_SITE when both are present."""
        # Create a temporary config file with both keys
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("EXPORT_SITES = ['Site1']\n")
            f.write("EXPORT_SITE = 'Site2'\n")
            f.write("EXPORT_TAGS = []\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)

            # EXPORT_SITES should take precedence
            assert config['export_sites'] == ['Site1']
        finally:
            os.unlink(config_path)

    def test_no_export_site_or_sites(self):
        """Test that config loads with neither EXPORT_SITE nor EXPORT_SITES."""
        # Create a temporary config file without site keys
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("EXPORT_TAGS = ['tag1']\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)

            # Should use default empty list
            assert config['export_sites'] == []
            assert isinstance(config['export_sites'], list)
        finally:
            os.unlink(config_path)

    def test_export_tags_loaded_correctly(self):
        """Test that EXPORT_TAGS is loaded correctly."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("EXPORT_TAGS = ['tag1', 'tag2']\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)

            # Verify tags are loaded
            assert config['export_tags'] == ['tag1', 'tag2']
            assert isinstance(config['export_tags'], list)
        finally:
            os.unlink(config_path)

    def test_default_values(self):
        """Test that default values are used when no config file is provided."""
        config = load_toml_config(None)

        # Verify default values
        assert config['export_sites'] == []
        assert config['export_tags'] == []
        assert config['export_interface_tags'] == []
        assert config['topology_name'] == ''
        assert config['export_configs'] is True

    def test_empty_config_file(self):
        """Test loading an empty config file uses defaults."""
        # Create an empty config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("")
            config_path = f.name

        try:
            config = load_toml_config(config_path)

            # Should use default values
            assert config['export_sites'] == []
            assert config['export_tags'] == []
        finally:
            os.unlink(config_path)
