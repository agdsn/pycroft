from legacy import convert
from pycroft import model

if __name__ == "__main__":
    print "drop old db model"
    model.drop_db_model()

    print "create new db model"
    model.create_db_model()

    print "convert data"
    convert.do_convert()
    print "complete"