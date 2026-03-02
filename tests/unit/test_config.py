"""Unit tests for configuration loading and backward compatibility."""

import os
import tempfile
from unittest import mock
from nrx.nrx import load_toml_config, load_config
from argparse import Namespace


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
            assert not config['export_sites']
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
        assert not config['export_sites']
        assert not config['export_tags']
        assert not config['export_interface_tags']
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
            assert not config['export_sites']
            assert not config['export_tags']
        finally:
            os.unlink(config_path)


class TestOutputDirConfig:
    """Test OUTPUT_DIR configuration from various sources."""

    def test_output_dir_from_config_file(self):
        """Test that OUTPUT_DIR is loaded from config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("OUTPUT_DIR = '/tmp/test_output'\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)
            assert config['output_dir'] == '/tmp/test_output'
        finally:
            os.unlink(config_path)

    def test_output_dir_from_env_var(self):
        """Test that OUTPUT_DIR environment variable is used."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("")
            config_path = f.name

        try:
            # Mock args
            args = Namespace(
                config=config_path,
                input='netbox',
                api='http://netbox.example.com',
                site='test-site',
                sites=None,
                tags=None,
                interface_tags=None,
                name=None,
                output=None,
                map=None,
                templates=None,
                dir=None,
                insecure=False,
                noconfigs=None,
                file=None
            )

            with mock.patch.dict(os.environ, {
                'OUTPUT_DIR': '/tmp/env_output',
                'NB_API_TOKEN': 'test_token'
            }):
                config = load_config(args)
                assert config['output_dir'] == '/tmp/env_output'
        finally:
            os.unlink(config_path)

    def test_output_dir_from_cli_arg(self):
        """Test that -D/--dir CLI argument takes precedence."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("OUTPUT_DIR = '/tmp/config_output'\n")
            config_path = f.name

        try:
            # Mock args with --dir parameter
            args = Namespace(
                config=config_path,
                input='netbox',
                api='http://netbox.example.com',
                site='test-site',
                sites=None,
                tags=None,
                interface_tags=None,
                name=None,
                output=None,
                map=None,
                templates=None,
                dir='/tmp/cli_output',
                insecure=False,
                noconfigs=None,
                file=None
            )

            with mock.patch.dict(os.environ, {
                'OUTPUT_DIR': '/tmp/env_output',
                'NB_API_TOKEN': 'test_token'
            }):
                config = load_config(args)
                assert config['output_dir'] == '/tmp/cli_output'
        finally:
            os.unlink(config_path)

    def test_output_dir_precedence_order(self):
        """Test precedence: CLI arg > env var > config file > default."""
        # Test 1: Config file only
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("OUTPUT_DIR = '/tmp/config_output'\n")
            config_path = f.name

        try:
            args = Namespace(
                config=config_path,
                input='netbox',
                api='http://netbox.example.com',
                site='test-site',
                sites=None,
                tags=None,
                interface_tags=None,
                name=None,
                output=None,
                map=None,
                templates=None,
                dir=None,
                insecure=False,
                noconfigs=None,
                file=None
            )

            with mock.patch.dict(os.environ, {'NB_API_TOKEN': 'test_token'}, clear=True):
                config = load_config(args)
                assert config['output_dir'] == '/tmp/config_output'
        finally:
            os.unlink(config_path)

        # Test 2: Env var overrides config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("OUTPUT_DIR = '/tmp/config_output'\n")
            config_path = f.name

        try:
            args.config = config_path
            with mock.patch.dict(os.environ, {
                'OUTPUT_DIR': '/tmp/env_output',
                'NB_API_TOKEN': 'test_token'
            }):
                config = load_config(args)
                assert config['output_dir'] == '/tmp/env_output'
        finally:
            os.unlink(config_path)

        # Test 3: CLI arg overrides everything
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("OUTPUT_DIR = '/tmp/config_output'\n")
            config_path = f.name

        try:
            args.config = config_path
            args.dir = '/tmp/cli_output'
            with mock.patch.dict(os.environ, {
                'OUTPUT_DIR': '/tmp/env_output',
                'NB_API_TOKEN': 'test_token'
            }):
                config = load_config(args)
                assert config['output_dir'] == '/tmp/cli_output'
        finally:
            os.unlink(config_path)

    def test_output_dir_default_empty(self):
        """Test that default output_dir is empty string."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("")
            config_path = f.name

        try:
            args = Namespace(
                config=config_path,
                input='netbox',
                api='http://netbox.example.com',
                site='test-site',
                sites=None,
                tags=None,
                interface_tags=None,
                name=None,
                output=None,
                map=None,
                templates=None,
                dir=None,
                insecure=False,
                noconfigs=None,
                file=None
            )

            with mock.patch.dict(os.environ, {'NB_API_TOKEN': 'test_token'}, clear=True):
                config = load_config(args)
                assert config['output_dir'] == ''
        finally:
            os.unlink(config_path)

    def test_output_dir_with_env_vars_expanded(self):
        """Test that environment variables in OUTPUT_DIR are expanded."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("OUTPUT_DIR = '$HOME/nrx_output'\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)
            # Should have expanded $HOME
            assert '$HOME' not in config['output_dir']
            assert config['output_dir'] == os.path.expandvars('$HOME/nrx_output')
        finally:
            os.unlink(config_path)


class TestTemplatesPathConfig:
    """Test TEMPLATES_PATH configuration from various sources."""

    def test_templates_path_from_config_file_string(self):
        """Test that TEMPLATES_PATH is loaded from config file as string."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("TEMPLATES_PATH = '/custom/templates'\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)
            assert config['templates_path'] == '/custom/templates'
        finally:
            os.unlink(config_path)

    def test_templates_path_from_config_file_list(self):
        """Test that TEMPLATES_PATH is loaded from config file as list."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("TEMPLATES_PATH = ['/path1/templates', '/path2/templates']\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)
            assert config['templates_path'] == ['/path1/templates', '/path2/templates']
        finally:
            os.unlink(config_path)

    def test_templates_path_from_env_var_string(self):
        """Test that TEMPLATES_PATH environment variable is used (string)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("")
            config_path = f.name

        try:
            args = Namespace(
                config=config_path,
                input='netbox',
                api='http://netbox.example.com',
                site='test-site',
                sites=None,
                tags=None,
                interface_tags=None,
                name=None,
                output=None,
                map=None,
                templates='/env/templates',
                dir=None,
                insecure=False,
                noconfigs=None,
                file=None
            )

            with mock.patch.dict(os.environ, {
                'TEMPLATES_PATH': '/env/templates',
                'NB_API_TOKEN': 'test_token'
            }):
                config = load_config(args)
                # CLI arg should prepend to the list
                assert '/env/templates' in config['templates_path']
        finally:
            os.unlink(config_path)

    def test_templates_path_from_cli_arg(self):
        """Test that -T/--templates CLI argument prepends to templates_path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("TEMPLATES_PATH = '/config/templates'\n")
            config_path = f.name

        try:
            args = Namespace(
                config=config_path,
                input='netbox',
                api='http://netbox.example.com',
                site='test-site',
                sites=None,
                tags=None,
                interface_tags=None,
                name=None,
                output=None,
                map=None,
                templates='/cli/templates',
                dir=None,
                insecure=False,
                noconfigs=None,
                file=None
            )

            with mock.patch.dict(os.environ, {'NB_API_TOKEN': 'test_token'}, clear=True):
                config = load_config(args)
                # CLI arg should be first in the list
                assert config['templates_path'][0] == '/cli/templates'
        finally:
            os.unlink(config_path)

    def test_templates_path_default_value(self):
        """Test that default templates_path is a list with default paths."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("")
            config_path = f.name

        try:
            config = load_toml_config(config_path)
            assert isinstance(config['templates_path'], list)
            assert './templates' in config['templates_path']
        finally:
            os.unlink(config_path)

    def test_templates_path_with_env_vars_expanded(self):
        """Test that environment variables in TEMPLATES_PATH are expanded."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("TEMPLATES_PATH = '$HOME/my_templates'\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)
            # Should have expanded $HOME
            assert '$HOME' not in config['templates_path']
            assert config['templates_path'] == os.path.expandvars('$HOME/my_templates')
        finally:
            os.unlink(config_path)

    def test_templates_path_list_with_env_vars_expanded(self):
        """Test that environment variables in TEMPLATES_PATH list are expanded."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("TEMPLATES_PATH = ['$HOME/templates1', '$HOME/templates2']\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)
            # Should have expanded $HOME in all list items
            assert all('$HOME' not in path for path in config['templates_path'])
            assert config['templates_path'][0] == os.path.expandvars('$HOME/templates1')
            assert config['templates_path'][1] == os.path.expandvars('$HOME/templates2')
        finally:
            os.unlink(config_path)


class TestPlatformMapConfig:
    """Test PLATFORM_MAP configuration from various sources."""

    def test_platform_map_from_config_file(self):
        """Test that PLATFORM_MAP is loaded from config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("PLATFORM_MAP = 'custom_platform_map.yaml'\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)
            assert config['platform_map'] == 'custom_platform_map.yaml'
        finally:
            os.unlink(config_path)

    def test_platform_map_from_env_var(self):
        """Test that PLATFORM_MAP environment variable is used."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("")
            config_path = f.name

        try:
            args = Namespace(
                config=config_path,
                input='netbox',
                api='http://netbox.example.com',
                site='test-site',
                sites=None,
                tags=None,
                interface_tags=None,
                name=None,
                output=None,
                map=None,
                templates=None,
                dir=None,
                insecure=False,
                noconfigs=None,
                file=None
            )

            with mock.patch.dict(os.environ, {
                'PLATFORM_MAP': 'env_platform_map.yaml',
                'NB_API_TOKEN': 'test_token'
            }):
                config = load_config(args)
                assert config['platform_map'] == 'env_platform_map.yaml'
        finally:
            os.unlink(config_path)

    def test_platform_map_from_cli_arg(self):
        """Test that -M/--map CLI argument takes precedence."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("PLATFORM_MAP = 'config_platform_map.yaml'\n")
            config_path = f.name

        try:
            args = Namespace(
                config=config_path,
                input='netbox',
                api='http://netbox.example.com',
                site='test-site',
                sites=None,
                tags=None,
                interface_tags=None,
                name=None,
                output=None,
                map='cli_platform_map.yaml',
                templates=None,
                dir=None,
                insecure=False,
                noconfigs=None,
                file=None
            )

            with mock.patch.dict(os.environ, {
                'PLATFORM_MAP': 'env_platform_map.yaml',
                'NB_API_TOKEN': 'test_token'
            }):
                config = load_config(args)
                assert config['platform_map'] == 'cli_platform_map.yaml'
        finally:
            os.unlink(config_path)

    def test_platform_map_precedence_order(self):
        """Test precedence: CLI arg > env var > config file > default."""
        # Test 1: Config file only
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("PLATFORM_MAP = 'config_map.yaml'\n")
            config_path = f.name

        try:
            args = Namespace(
                config=config_path,
                input='netbox',
                api='http://netbox.example.com',
                site='test-site',
                sites=None,
                tags=None,
                interface_tags=None,
                name=None,
                output=None,
                map=None,
                templates=None,
                dir=None,
                insecure=False,
                noconfigs=None,
                file=None
            )

            with mock.patch.dict(os.environ, {'NB_API_TOKEN': 'test_token'}, clear=True):
                config = load_config(args)
                assert config['platform_map'] == 'config_map.yaml'
        finally:
            os.unlink(config_path)

        # Test 2: Env var overrides config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("PLATFORM_MAP = 'config_map.yaml'\n")
            config_path = f.name

        try:
            args.config = config_path
            with mock.patch.dict(os.environ, {
                'PLATFORM_MAP': 'env_map.yaml',
                'NB_API_TOKEN': 'test_token'
            }):
                config = load_config(args)
                assert config['platform_map'] == 'env_map.yaml'
        finally:
            os.unlink(config_path)

        # Test 3: CLI arg overrides everything
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("PLATFORM_MAP = 'config_map.yaml'\n")
            config_path = f.name

        try:
            args.config = config_path
            args.map = 'cli_map.yaml'
            with mock.patch.dict(os.environ, {
                'PLATFORM_MAP': 'env_map.yaml',
                'NB_API_TOKEN': 'test_token'
            }):
                config = load_config(args)
                assert config['platform_map'] == 'cli_map.yaml'
        finally:
            os.unlink(config_path)

    def test_platform_map_default_value(self):
        """Test that default platform_map is NRX_MAP_NAME."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("")
            config_path = f.name

        try:
            config = load_toml_config(config_path)
            assert config['platform_map'] == 'platform_map.yaml'
        finally:
            os.unlink(config_path)

    def test_platform_map_with_env_vars_expanded(self):
        """Test that environment variables in PLATFORM_MAP are expanded."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("PLATFORM_MAP = '$HOME/my_platform_map.yaml'\n")
            config_path = f.name

        try:
            config = load_toml_config(config_path)
            # Should have expanded $HOME
            assert '$HOME' not in config['platform_map']
            assert config['platform_map'] == os.path.expandvars('$HOME/my_platform_map.yaml')
        finally:
            os.unlink(config_path)
