# SPDX-FileCopyrightText: 2025-present Data & Web Science Lab AUTh <gounaria@csd.auth.gr>
#
# SPDX-License-Identifier: Apache 2.0
import logging
from streamdaq.logging import configure_logging

# Automatically bootstrap with sensible defaults on initial package import
configure_logging(level=logging.INFO, pathway_level=logging.WARNING, enable_console=True)
