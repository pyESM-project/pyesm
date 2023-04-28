import pprint as pp
import pandas as pd

def prettify(item: dict) -> None:
    """Print a dictionary in a human-readable format in the terminal

    Args:
        item (dict): a generic dictionary

    Raises:
        TypeError: If the argument is not a dictionary.
    """
    if not isinstance(item, dict):
        raise TypeError('Function argument should be a dictionary.')
    print(pp.pformat(item))


def find_dict_depth(item) -> int:
    """Find and return the depth of a generic dictionary

    Args:
        item (dict): a generic dictionary

    Returns:
        int: depth of the dictionary
    """
    if not isinstance(item, dict) or not item:
        return 0
    return 1 + max(find_dict_depth(v) for k, v in item.items())


def write_excel(
          excel_file_path: str,
          dict_name: dict,
          headers: str,
          writer_engine: str = 'openpyxl',

          ):
            """Support function to generate excel"""
            with pd.ExcelWriter(excel_file_path, engine=writer_engine) as writer:
                for sheet_name, value in dict_name.items():
                    dataframe = pd.DataFrame(
                        columns=value[headers])
                    sheet = writer.book.create_sheet(sheet_name)
                    writer.sheets[sheet_name] = sheet
                    dataframe.to_excel(
                        writer,
                        sheet_name=sheet_name,
                        index=False
                    )

if __name__ == '__main__':
    pass
