"""Example agent plug-in that logs a greeting at startup."""

import logging


def register():
    logging.getLogger(__name__).info("Hello from plug-in")
