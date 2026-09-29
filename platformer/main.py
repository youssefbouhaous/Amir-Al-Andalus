import logging
import sys

import pygame

from core.game import Game

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    # pygame.init() never raises; it reports modules that failed (e.g. no
    # audio device). The game must still run without sound, so just log it.
    _, failed_modules = pygame.init()
    if failed_modules:
        logger.warning("%d pygame module(s) failed to initialise", failed_modules)

    try:
        Game().run()
    except pygame.error as error:
        logger.critical("Pygame error: %s", error)
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted, shutting down")
    finally:
        pygame.quit()

    return 0


if __name__ == "__main__":
    sys.exit(main())
