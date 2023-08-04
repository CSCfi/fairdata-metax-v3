import argparse
import ast
import copy
import hashlib
import io
import logging
import os
import re
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(
    description="Generate reference markdown files to docs/reference."
)
parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument(
    "-d",
    "--delete-obsolete",
    action="store_true",
    help="Delete obsolete markdown files and empty directories from reference.",
)
parser.add_argument(
    "-g",
    "--git-files-only",
    action="store_true",
    help=("Use file versions staged or committed in git. " "Excludes files not tracked by git."),
)
settings = parser.parse_args()


loglevel = logging.DEBUG if settings.verbose else logging.INFO
logging.basicConfig(level=loglevel, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__file__)

REFERENCE_PATH = "docs/reference/"


def run_git_command(*git_args) -> str:
    """Run git command, return stdout."""
    result = subprocess.run(
        [
            "git",
            *git_args,
        ],
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    if result.stderr != "":
        raise ValueError(f"Error: {result.stderr}")
    return result.stdout


def get_git_files() -> list:
    """Return list of files tracked by git."""
    return run_git_command("ls-files").splitlines()


def get_git_staged_file_content(path) -> str:
    """Return staged or committed version of file content."""
    return run_git_command("show", f":{path}")


def get_file_md5(path) -> str:
    with open(path, "rb") as file:
        return hashlib.md5(file.read()).hexdigest()


def get_ast(path) -> ast.Module:
    """Parse Abstract Syntax Tree from python file."""
    with open(path, "rt") as file:
        if settings.git_files_only:
            return ast.parse(get_git_staged_file_content(path), filename=path)
        else:
            return ast.parse(file.read(), filename=path)


def get_node_items(node) -> list:
    """Get names of functions and classes in AST node."""
    return list(
        f.name for f in node if isinstance(f, ast.FunctionDef) or isinstance(f, ast.ClassDef)
    )


def get_items(path) -> list:
    """Return top-level items from Python file using AST parser."""
    tree = get_ast(path)
    return get_node_items(tree.body)


def get_md_data(module) -> dict:
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


def module_tree(modules: list) -> list:
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


def update_file(path, contents: io.StringIO) -> None:
    """Write contents to file if changed."""
    is_new = True
    changed = True
    if os.path.isfile(path):
        is_new = False
        new_md5 = hashlib.md5(contents.getvalue().encode("utf-8")).hexdigest()
        old_md5 = get_file_md5(path)
        changed = new_md5 != old_md5

    if changed:
        if is_new:
            logger.info(f"Creating: {path}")
        else:
            logger.info(f"Updating: {path}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(contents.getvalue())
    else:
        logger.debug(f"Unchanged: {path}")


def write_module_doc(module) -> str:
    """Write reference documentation file for module.

    Returns path of file.
    """
    if not module["items"]:
        return

    md_data = get_md_data(module)
    md_path = md_data["path"]

    try:
        os.makedirs(md_path.rsplit("/", 1)[0])  # make directory if it does not exist
    except FileExistsError:
        pass

    contents = io.StringIO()
    print(f"# {module['name']}", file=contents)
    print(file=contents)

    for s in module["items"]:
        print(f"## {s}", file=contents)
        print(file=contents)
        print(f"### :::{module['fullname']}.{s}", file=contents)
        print(file=contents)

    update_file(md_path, contents)
    return md_path


def write_summary(modules) -> str:
    """Write SUMMARY.md for reference.

    Returns path of file."""
    summary_path = REFERENCE_PATH + "SUMMARY.md"
    contents = io.StringIO()

    def recurse(module, level):
        md_data = get_md_data(module)
        path = re.sub("^" + re.escape(REFERENCE_PATH), "", md_data["path"])
        title = module["fullname"]
        if parent := module.get("parent"):
            title = title.replace(parent["fullname"] + ".", "", 1)
        if module["items"]:
            print(f"{' ' * (level*4)}- [{title}]({path})", file=contents)
        else:
            print(f"{' ' * (level*4)}- {title}", file=contents)
        for child in sorted(module["children"], key=lambda m: m["fullname"]):
            recurse(child, level=level + 1)

    roots = [module for module in modules if module["parent"] is None]
    for module in roots:
        recurse(module, level=0)

    update_file(summary_path, contents)
    return summary_path


def remove_empty_dirs() -> int:
    count = 0
    walk = list(os.walk(REFERENCE_PATH))
    for path, _, _ in walk[::-1]:
        if len(os.listdir(path)) == 0:
            logger.info(f"Deleting empty directory: {path}")
            os.rmdir(path)
            count += 1
    return count


def handle_obsolete_files(used_files) -> None:
    files = Path(REFERENCE_PATH).rglob("*.md")
    obsolete_files = []
    for file in files:
        path = str(file.as_posix())
        if path not in used_files:
            obsolete_files.append(path)

    if settings.delete_obsolete:
        for path in obsolete_files:
            logger.info(f"Deleting obsolete file: {path}")
            os.remove(path)
        removed_dir_count = remove_empty_dirs()
        removed_msgs = []
        if obsolete_files:
            removed_msgs.append(f"{len(obsolete_files)} obsolete markdown files")
        if removed_dir_count > 0:
            removed_msgs.append(f"{removed_dir_count} empty directories")
        if removed_msgs:
            logger.info(f"Deleted {' and '.join(removed_msgs)}.")
    else:
        for path in obsolete_files:
            logger.info(f"Obsolete file: {path}")
        if obsolete_files:
            logger.info(
                f"Found {len(obsolete_files)} obsolete markdown files. "
                "Add argument -d to delete obsolete files and empty directories from reference."
            )


def write_docs(modules: list) -> None:
    """Create module tree and write reference markdown files."""
    modules = module_tree(modules)

    used_files = set()
    for module in modules:
        used_files.add(write_module_doc(module))
    used_files.add(write_summary(modules))

    handle_obsolete_files(used_files)
    logger.info(f"Reference updated.")


def generate_refs(packages, exclude=[], include_only_files=None) -> None:
    """Analyze python files from package directories and write reference documentation."""
    modules = []
    for package in packages:
        files = Path(package).rglob("*.py")
        for file in files:
            path = str(file.as_posix())
            skip = False

            if include_only_files is not None:
                # only include file specific files
                if path not in include_only_files:
                    logger.debug(f"Skip file (not in include): {path}")
                    continue

            for exclude_path in exclude:
                if exclude_path in path:
                    skip = True
                    logger.debug(f"Skip file (path excluded): {path}")
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


include_only_files = None
if settings.git_files_only:
    include_only_files = get_git_files()

generate_refs(
    ["src/apps", "tests"], exclude=["/migrations/"], include_only_files=include_only_files
)
