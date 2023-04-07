from pySM.log_exc.logger import Logger


class Problem:

    def __init__(
            self,
            logger: Logger) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"Generation of '{str(self)}' object...")
        self.logger.info(f"'{str(self)}' object generated.")

    def __str__(self):
        class_name = type(self).__name__
        return f'{class_name}'


if __name__ == '__main__':
    pass
