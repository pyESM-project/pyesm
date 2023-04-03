from pySM.log_exc.logger import Logger


class Problem:

    def __init__(
            self,
            logger: Logger) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info('Generation of Problem object...')
        self.logger.info('Problem object generated.')


if __name__ == '__main__':
    pass
