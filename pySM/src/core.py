"""Basic functions for generating and launching the model."""
from pySM.src.constants import _PATHS
from pySM.src.model import Model
from pySM.src.file_manager import FileManager


class Core:

    def __init__(
            self,
            file_config='case_config.json',
            sets_file_name='sets.xlsx'):
        """Generation of interface: loading model, database, case information."""

        self.model = Model()
        self.sets_dict = self.model.database.sets

        self.file_manager = FileManager(
            dir_path=f"{_PATHS['case_root']}/{_PATHS['case_folder']}",
            sets_file_name=sets_file_name
        )

        self.case_config = self.file_manager.load_config(file_config)
        self.file_manager.generate_excel_empty_sets(
            sets_dict=self.model.database.sets,
            sets_dir_path=self.file_manager.dir_path,
            sets_file_name=self.file_manager.sets_file_name
        )

    def get_sets_data(self):
        self.sets_dict_data = self.file_manager.read_excel_sets_data(
            sets_dict=self.sets_dict,
            sets_dir_path=self.file_manager.dir_path,
            sets_file_name=self.file_manager.sets_file_name
        )


if __name__ == '__main__':

    # needed to launch the load_config directly from terminal
    # __file__ = 'D:\git_repos\pySM\pySM\interface\interface.py'

    i1 = Core()
    i1.get_sets_data()

    # preparation of input files to be filled
    # filling the sets file manually, then importing data and store in database
    #

    # print(config['paths']['model_data'])
