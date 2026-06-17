# SPDX-FileCopyrightText: 2025-present Data & Web Science Lab AUTh <gounaria@csd.auth.gr>
#
# SPDX-License-Identifier: Apache 2.0
import logging as std_logging  # Alias to prevent namespace clashing during bootstrap
from streamdaq.logging import configure_logging

# Automatically bootstrap with sensible defaults on initial package import
configure_logging(level=std_logging.INFO, pathway_level=std_logging.WARNING, enable_console=True)
