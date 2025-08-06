"""Path: ffbPlayerDraftingApp/backend/logging_config.py"""

import logging
import sys

from pythonjsonlogger import jsonlogger

# 1. Create a logger instance with a fixed name for the whole application.
log = logging.getLogger("ffb-backend")
log.setLevel(logging.INFO)

# 2. Prevent the log from being handled by the root logger, which can cause
#    duplicate output in some environments.
log.propagate = False

# 3. Clear existing handlers to avoid adding them multiple times, which can
#    happen in interactive sessions or with some web frameworks.
if log.hasHandlers():
    log.handlers.clear()

# 4. Create a handler to direct logs to standard output (the terminal).
handler = logging.StreamHandler(sys.stdout)

# 5. Define the format for our structured JSON logs.
formatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
handler.setFormatter(formatter)

# 6. Add the configured handler to our logger.
log.addHandler(handler)

# Now, any file can just 'from backend.logging_config import log' to use it.
