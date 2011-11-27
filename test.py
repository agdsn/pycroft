from pycroft import model
model.create_db_model()
#model.drop_db_model()
model.session.session.flush()
