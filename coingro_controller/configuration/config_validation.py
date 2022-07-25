import logging
from typing import Any, Dict

from coingro.configuration.config_validation import CoingroValidator
from jsonschema import Draft4Validator
from jsonschema.exceptions import ValidationError, best_match

from coingro_controller.constants import CONTROLLER_CONF_SCHEMA


logger = logging.getLogger(__name__)


def validate_config_schema(conf: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the configuration follow the Config Schema
    :param conf: Config in JSON format
    :return: Returns the config if valid, otherwise throw an exception
    """
    try:
        CoingroValidator(CONTROLLER_CONF_SCHEMA).validate(conf)
        return conf
    except ValidationError as e:
        logger.critical(
            f"Invalid configuration. Reason: {e}"
        )
        raise ValidationError(
            best_match(Draft4Validator(CONTROLLER_CONF_SCHEMA).iter_errors(conf)).message
        )


def validate_config_consistency(conf: Dict[str, Any]) -> None:
    """
    Validate the configuration consistency.
    Should be ran after loading both configuration and strategy,
    since strategies can set certain configuration settings too.
    :param conf: Config in JSON format
    :return: Returns None if everything is ok, otherwise throw an exception
    """

    # validate configuration before returning
    logger.info('Validating configuration ...')
    validate_config_schema(conf)
