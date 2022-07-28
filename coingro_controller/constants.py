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
        'cg_env_vars': {'type': 'object'},
        'cg_initial_state': {'type': 'string', 'enum': ['running', 'stopped']},
        'cg_api_router_prefix': {'type': 'string'},
        'cg_api_server_port': {
            'type': 'integer',
            'minimum': 1024,
            'maximum': 65535
        },
        'cg_api_server_username': {'type': 'string'},
        'cg_api_server_password': {'type': 'string'},
        'cg_strategies_pvc_claim': {'type': 'string'},
        'cg_version': {'type': 'string'},
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
    'required': ['cg_image', 'cg_version', 'api_server']
}
