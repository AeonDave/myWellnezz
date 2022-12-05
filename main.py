import os

import constants
from models.mywellnezz import MyWellnezz
from modules import update

if __name__ == '__main__':
    update.update_github('AeonDave', 'MyWellnezzPublic', constants.version)
    update.delete_old_versions(os.path.dirname(update.self_path()), constants.name, constants.version)
    MyWellnezz().main()
