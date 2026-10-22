import glob
import os
import shutil
import time

import yaml

class ConfigManager:
    _instance = None

    def __init__(self):
        """Initialize the ConfigManager instance."""
        self.config = None
        self.schema = None

    @classmethod
    def initialize(cls, schema_path=None):
        """Initialize the ConfigManager with the given schema path."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.schema = cls._instance.load_config_schema(schema_path)
            cls._instance.config = cls._instance.load_default_config()
            cls._instance.load_user_config()

    @classmethod
    def get_schema(cls):
        """Get the configuration schema."""
        if cls._instance is None:
            raise RuntimeError("ConfigManager not initialized")
        return cls._instance.schema

    @classmethod
    def get_config_section(cls, *keys):
        """Get a specific section of the configuration."""
        if cls._instance is None:
            raise RuntimeError("ConfigManager not initialized")

        section = cls._instance.config
        for key in keys:
            if isinstance(section, dict) and key in section:
                section = section[key]
            else:
                return {}
        return section

    @classmethod
    def get_config_value(cls, *keys):
        """Get a specific configuration value using nested keys."""
        if cls._instance is None:
            raise RuntimeError("ConfigManager not initialized")

        value = cls._instance.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    @classmethod
    def set_config_value(cls, value, *keys):
        """Set a specific configuration value using nested keys."""
        if cls._instance is None:
            raise RuntimeError("ConfigManager not initialized")

        config = cls._instance.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            elif not isinstance(config[key], dict):
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value

    @staticmethod
    def load_config_schema(schema_path=None):
        """Load the configuration schema from a YAML file."""
        if schema_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            schema_path = os.path.join(base_dir, 'config_schema.yaml')

        # Always UTF-8. Left to the default, open() decodes with the system code
        # page - cp1251 on a Russian Windows - and a non-ASCII value in the file
        # turns into different characters without any error to show for it.
        with open(schema_path, 'r', encoding='utf-8') as file:
            schema = yaml.safe_load(file)
        return schema

    def load_default_config(self):
        """Load default configuration values from the schema."""
        def extract_value(item):
            if isinstance(item, dict):
                if 'value' in item:
                    return item['value']
                else:
                    return {k: extract_value(v) for k, v in item.items()}
            return item

        config = {}
        for category, settings in self.schema.items():
            config[category] = extract_value(settings)
        return config

    def load_user_config(self, config_path=os.path.join('src', 'config.yaml')):
        """Load user configuration and merge with default config."""
        def deep_update(source, overrides):
            for key, value in overrides.items():
                if isinstance(value, dict) and key in source:
                    deep_update(source[key], value)
                else:
                    source[key] = value

        if config_path and os.path.isfile(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as file:
                    user_config = yaml.safe_load(file)
                    self._migrate(user_config)
                    deep_update(self.config, user_config)
            except yaml.YAMLError:
                print("Error in configuration file. Using default configuration.")

    @staticmethod
    def _migrate(user_config):
        """
        Carry settings written by older versions over to their current names.

        `misc.print_to_terminal` became `misc.write_status_log`. The old name
        promised a terminal that does not exist under pythonw - the output went
        to ww_out.log - and the same switch wrote every transcription there in
        full. Its value now governs only the status log. The dictated text has
        its own switch, which is off unless set, so upgrading stops writing it
        rather than carrying a silent `true` across.
        """
        misc = (user_config or {}).get('misc')
        if isinstance(misc, dict) and 'print_to_terminal' in misc:
            old = misc.pop('print_to_terminal')
            misc.setdefault('write_status_log', old)

    @classmethod
    def save_config(cls, config_path=os.path.join('src', 'config.yaml')):
        """
        Save the current configuration to a YAML file.

        The write is wholesale: yaml.dump emits the settings the app is holding
        and nothing else, so hand-written comments in the file are gone and any
        value the settings window failed to round-trip is gone with them. Keep
        a dated copy of what was there before, so a bad save is recoverable.
        """
        if cls._instance is None:
            raise RuntimeError("ConfigManager not initialized")

        cls._backup_config(config_path)

        with open(config_path, 'w', encoding='utf-8') as file:
            yaml.dump(cls._instance.config, file, default_flow_style=False)

    # How many dated backups to keep. Each one is under two kilobytes, and a
    # mistake usually shows up within a day or two of making it.
    _BACKUP_KEEP = 5

    @classmethod
    def _backup_config(cls, config_path):
        """
        Copy the existing config aside before it is overwritten.

        One backup per day: the first save of the day preserves the state the
        day started in, which is the version worth going back to. Failure here
        must never block a save - a read-only folder loses the safety net, not
        the setting the user just changed.
        """
        if not os.path.isfile(config_path):
            return

        stamp = time.strftime('%Y-%m-%d')
        backup = f'{config_path}.backup-{stamp}'
        try:
            if not os.path.exists(backup):
                shutil.copy2(config_path, backup)

            older = sorted(glob.glob(f'{config_path}.backup-*'), reverse=True)
            for stale in older[cls._BACKUP_KEEP:]:
                os.remove(stale)
        except OSError as e:
            print(f'Could not back up the configuration: {e}')

    @classmethod
    def reload_config(cls):
        """
        Reload the configuration from the file.
        """
        if cls._instance is None:
            raise RuntimeError("ConfigManager not initialized")
        cls._instance.config = cls._instance.load_default_config()
        cls._instance.load_user_config()

    @classmethod
    def config_file_exists(cls):
        """Check if a valid config file exists."""
        config_path = os.path.join('src', 'config.yaml')
        return os.path.isfile(config_path)

    @classmethod
    def console_print(cls, message):
        """Print a message to the console if enabled in the configuration."""
        if cls._instance and cls._instance.config['misc']['write_status_log']:
            print(message)
