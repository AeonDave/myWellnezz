import os

import constants
from main_loop import main
from models.mywellnezz import MyWellnezz
from modules import update

if __name__ == '__main__':
    update.check_new_versions(os.path.dirname(update.self_path()), constants.name, constants.version)
    update.update_github('AeonDave', 'MyWellnezzPublic', constants.version)
    update.delete_old_versions(os.path.dirname(update.self_path()), constants.name, constants.version)
    print('[Starting...]')
    main(MyWellnezz())
