import ast
import copy
import logging
import os
import re
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__file__)

REFERENCE_PATH = "docs/reference/"


def get_ast(path):
    """Parse Abstract Syntax Tree from python file."""
    with open(path, "rt") as file:
        return ast.parse(file.read(), filename=path)


def get_node_items(node):
    """Get names of functions and classes in AST node."""
    return list(
        f.name for f in node if isinstance(f, ast.FunctionDef) or isinstance(f, ast.ClassDef)
    )


def get_items(path):
    """Return top-level items from Python file using AST parser."""
    tree = get_ast(path)
    return get_node_items(tree.body)


def get_md_data(module):
    """Get markdown file path data for module."""
    is_pkg = False
    path = module["path"]
    if path.endswith("__init__.py"):
        md_path = path[: -len("__init__.py")] + "index.md"
        is_pkg = True
    elif path.endswith(".py"):
        md_path = path[:-3] + ".md"
    else:
        raise ValueError(f"not a .py file: {module['path']}")
    md_path = REFERENCE_PATH + md_path
    return {"path": md_path, "is_pkg": is_pkg}


def module_tree(modules):
    """Create module hierarchy."""
    modules = copy.deepcopy(modules)
    for module in modules:
        module["children"] = []
        module["parent"] = None

    modules_by_fullname = {m["fullname"]: m for m in modules}
    names = [m["fullname"] for m in modules]

    # assign parent relations based on module names
    parents = {}
    for name in sorted(names):
        parents[name] = ""
        # try different name parts to see if such modules exist,
        # e.g. for module a.b.c.d try a, a.b, and a.b.c
        split = name.split(".")
        for i in range(len(split)):
            prefix = ".".join(split[:i])
            if prefix in names:
                parents[name] = prefix  # longest match will be the parent

    for child, parent in parents.items():
        if parent != "":
            modules_by_fullname[child]["parent"] = modules_by_fullname[parent]

    # assign child relations based on parent relations
    children = {}
    for child, parent in parents.items():
        if parent not in children:
            children[parent] = []
        children[parent].append(child)
    for parent, parent_children in children.items():
        if parent != "":
            modules_by_fullname[parent]["children"] = [
                modules_by_fullname[c] for c in parent_children
            ]

    # skip uninteresting modules
    changed = True
    while changed:  # iterate until no more changes happened
        changed = False
        # mark modules with no content and no more than 1 child to be skipped
        for module in modules:
            children = module["children"]
            if len(children) <= 1 and not module["items"]:
                module["skip"] = True
                changed = True

        # assign children of skipped modules to grandparent
        for module in modules:
            if module.get("skip"):
                children = module["children"]
                parent = module["parent"]
                for child in children:
                    child["parent"] = parent
                if parent:
                    parent["children"] = [c for c in parent["children"] if c is not module]
                    parent["children"].extend(children)
        modules = [
            module for module in modules if not module.get("skip")
        ]  # remove skipped modules from list
    return modules


def write_module_doc(module):
    """Write reference documentation file for module."""
    if not module["items"]:
        return

    md_data = get_md_data(module)
    md_path = md_data["path"]

    try:
        os.makedirs(md_path.rsplit("/", 1)[0])  # make directory if it does not exist
    except FileExistsError:
        pass
    with open(md_path, "w") as f:
        logger.info(f"Creating: {md_path}")
        print(f"# {module['name']}", file=f)
        print(file=f)

        for s in module["items"]:
            print(f"## {s}", file=f)
            print(file=f)
            print(f"### :::{module['fullname']}.{s}", file=f)
            print(file=f)


def write_summary(modules):
    """Write SUMMARY.md for reference."""
    summary_path = REFERENCE_PATH + "SUMMARY.md"
    logger.info(f"Creating: {summary_path}")
    with open(summary_path, "w") as f:

        def recurse(module, level):
            md_data = get_md_data(module)
            path = re.sub("^" + re.escape(REFERENCE_PATH), "", md_data["path"])
            title = module["fullname"]
            if parent := module.get("parent"):
                title = title.replace(parent["fullname"] + ".", "", 1)
            if module["items"]:
                print(f"{' ' * (level*4)}- [{title}]({path})", file=f)
            else:
                print(f"{' ' * (level*4)}- {title}", file=f)
            for child in sorted(module["children"], key=lambda m: m["fullname"]):
                recurse(child, level=level + 1)

        roots = [module for module in modules if module["parent"] is None]
        for module in roots:
            recurse(module, level=0)


def write_docs(modules):
    """Create module tree and write reference markdown files."""
    modules = module_tree(modules)
    for module in modules:
        write_module_doc(module)
    write_summary(modules)


def generate_refs(packages, exclude=[]):
    """Analyze python files from package directories and write reference documentation."""
    modules = []
    for package in packages:
        files = Path(package).rglob("*.py")
        for file in files:
            path = str(file.as_posix())
            skip = False
            for exclude_path in exclude:
                if exclude_path in path:
                    skip = True
                    break
            if skip:
                continue
            modname = re.sub("(/__init__)?\.py$", "", path).replace("/", ".")
            items = get_items(path)

            modules.append(
                dict(
                    fullname=modname,
                    name=modname.rsplit(".", 1)[-1],
                    path=path,
                    items=items,
                )
            )
    write_docs(modules)


generate_refs(["src/apps", "tests"], exclude=["/migrations/"])
