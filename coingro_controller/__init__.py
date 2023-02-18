""" Coingro k8s module """
import os

__version__ = "1.0.4"
__id__ = os.environ.get("CG_CONTROLLER_ID", "coingro-controller")
__env__ = os.environ.get("CG_CONTROLLER_APP_ENV", "")
__group__ = os.environ.get("CG_CONTROLLER_GROUP", "worker")
