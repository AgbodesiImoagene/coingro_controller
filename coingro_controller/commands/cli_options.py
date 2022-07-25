from coingro.commands.cli_options import Arg

from coingro_controller import __version__
from coingro_controller.constants import DEFAULT_CONFIG


AVAILABLE_CLI_OPTIONS = {
    "verbosity": Arg(
        '-v', '--verbose',
        help='Verbose mode (-vv for more, -vvv to get all messages).',
        action='count',
        default=0,
    ),
    "logfile": Arg(
        '--logfile',
        help="Log to the file specified. Special values are: 'syslog', 'journald', 'default'. "
             "See the documentation for more details.",
        metavar='FILE',
    ),
    "version": Arg(
        '-V', '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    ),
    "config": Arg(
        '-c', '--config',
        help=f'Specify configuration file (default: `config/{DEFAULT_CONFIG}` '
        f'or `{DEFAULT_CONFIG}` whichever exists).'
        f'Multiple --config options may be used. '
        f'Can be set to `-` to read config from stdin.',
        action='append',
        metavar='PATH',
    ),
    "user_data_dir": Arg(
        '--userdir', '--user-data-dir',
        help='Path to userdata directory. This directory will contain the bot strategies.',
        metavar='PATH',
    ),
    "sd_notify": Arg(
        '--sd-notify',
        help='Notify systemd service manager.',
        action='store_true',
    ),
}
