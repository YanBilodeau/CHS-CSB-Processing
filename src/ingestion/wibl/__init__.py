import sys
from importlib import resources
from pathlib import Path

__version__ = "1.0.0"


def get_default_file(default_file_rel_path: str) -> Path:
    """
    Get path of resource file stored in ``wibl.defaults`` module from its location
    in the current installation of wibl-python.
    :param default_file_rel_path:
    :return:
    """
    if sys.version_info[0] == 3 and sys.version_info[1] < 9:
        # Python version is less than 3.9, so use older method of resolving resource files
        path_elems = default_file_rel_path.split("/")
        fname = path_elems[-1]
        sub_mod = ".".join(path_elems[:-1])
        with resources.path(f"wibl.defaults.{sub_mod}", fname) as schema_file:
            return schema_file
    else:
        # Python version is >= 3.9, so use newer, non-deprecated resource resolution method
        return Path(
            str(resources.files("wibl").joinpath(f"defaults/{default_file_rel_path}"))
        )
