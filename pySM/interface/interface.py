"""Basic functions for generating and launching the model."""

import os
import json

from pySM.model.model import Model


class Interface:
    """Model generation, setup and run."""

    def __init__(self, config_file_name: str):
        self.config = self.load_config(config_file_name)
        self.model = Model()

    def load_config(self, config_file_name: str):
        """Get the model json configuration file."""
        config_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                   config_file_name)
        with open(config_path, 'r') as file:
            return json.load(file)


# def generate_input_files():
#     """Generate input data file with sets structure."""
#     pass
#     config = load_config('case_config.json')


if __name__ == '__main__':

    # needed to launch the load_config directly from terminal
    # __file__ = 'D:\git_repos\pySM\pySM\interface\interface.py'

    i1 = Interface('case_config.json')

    # step 1: preparation of input files to be filled

    # print(config['paths']['model_data'])
