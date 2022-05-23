import json


def md_row(*items: str) -> str:
    return "| " + " | ".join(items) + " |"


if __name__ == "__main__":
    import sys

    filename = sys.argv[1]
    with open(filename) as f:
        j = json.load(f)

    COLS = "current wanted latest dependent".split()  # don't care about location
    print(f"### :warning: {len(j)} Outdated NPM packages")
    print()
    print(md_row("package", *COLS))
    print(md_row(*["---"] * 5))
    for package, props in j.items():
        print(md_row(package, *(props[x] for x in COLS)))
