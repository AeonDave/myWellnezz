import constants
from models.mywellnezz import MyWellnezz
from modules import update

if __name__ == '__main__':
    update.update_github('AeonDave', 'MyWellnezzPublic', constants.version)
    MyWellnezz().main()
