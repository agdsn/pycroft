

def bake_endpoint(blueprint, fn):
    return "%s.%s" % (blueprint.name, fn.__name__)
