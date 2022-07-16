""" Coingro k8s module """
import os


__version__ = 'dev'
__id__ = os.environ.get('CG_CONTROLLER_ID', 'coingro-controller')
__env__ = os.environ.get('CG_CONTROLLER_APP_ENV')
