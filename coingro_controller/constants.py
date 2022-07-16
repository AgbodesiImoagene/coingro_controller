DEFAULT_CONFIG = 'config.json'
DEFAULT_DB_URL = 'sqlite:///controllerv1.sqlite'
DEFAULT_NAMESPACE = 'coingro'

TELEGRAM_SETTING_OPTIONS = ['on', 'off', 'silent']
WEBHOOK_FORMAT_OPTIONS = ['form', 'json', 'raw']

DRIVERNAME_OPTIONS = ['mysql', 'postgresql', 'sqlite']

ENV_VAR_PREFIX = 'COINGRO_CONTROLLER__'

# Required json-schema for user specified config
CONTROLLER_CONF_SCHEMA = {
    'type': 'object',
    'properties': {
        'namespace': {'type': 'string'},
        'cg_image': {'type': 'string'},
        'cg_image_config': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'repository': {'type': 'string'},
                'tag': {'type': 'string'},
                'registry_host': {
                    'anyOf': [
                        {'format': 'hostname'},
                        {'format': 'ipv4'},
                        {'format': 'ipv6'},
                    ]
                },
                'registry_port': {
                    'type': 'integer',
                    'minimum': 1024,
                    'maximum': 65535
                },
            }
            'required': ['name', 'tag']
        },
        'cg_image_pull_secrets': {'type': 'array', 'items': {'type': 'string'}},
        'cg_env_vars': {'type': 'object'},
        'cg_api_server_port': {
            'type': 'integer',
            'minimum': 1024,
            'maximum': 65535
        },
        'cg_api_server_username': {'type': 'string'},
        'cg_api_server_password': {'type': 'string'},
        'cg_data_pvc_claim': {'type': 'string'},
        'api_server': {
            'type': 'object',
            'properties': {
                'enabled': {'type': 'boolean'},
                'listen_ip_address': {'format': 'ipv4'},
                'listen_port': {
                    'type': 'integer',
                    'minimum': 1024,
                    'maximum': 65535
                },
                'jwt_secret_key': {'type': 'string'},
                'CORS_origins': {'type': 'array', 'items': {'type': 'string'}},
                'verbosity': {'type': 'string', 'enum': ['error', 'info']},
            },
            'required': ['enabled', 'listen_ip_address', 'listen_port']
        },
        'db_config': {
            'type': 'object',
            'properties': {
                'drivername': {'type': 'string', 'enum': DRIVERNAME_OPTIONS},
                'username': {'type': 'string'},
                'password': {'type': 'string'},
                'host': {
                    'anyOf': [
                        {'format': 'hostname'},
                        {'format': 'ipv4'},
                        {'format': 'ipv6'},
                    ]
                },
                'port': {
                    'type': 'integer',
                    'minimum': 1024,
                    'maximum': 65535
                },
                'database': {'type': 'string'},
                'query': {'type': 'object', 'default': {}}
            },
            'required': ['drivername']
        },
        'db_url': {'type': 'string'},
        'encryption': {'type': 'boolean', 'default': False},
        'initial_state': {'type': 'string', 'enum': ['running', 'stopped']},
        'internals': {
            'type': 'object',
            'default': {},
            'properties': {
                'process_throttle_secs': {'type': 'integer'},
                'interval': {'type': 'integer'},
                'sd_notify': {'type': 'boolean'},
            }
        },
    },
    'required': ['coingro_image', 'api_server']
}
