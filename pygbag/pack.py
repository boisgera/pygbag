import sys, os
import zipfile
from pathlib import Path

# rm $(find |grep pygbag.png$)
# pngquant -f --ext -pygbag.png --quality 40 $(find|grep png$)


COUNTER = 0
TRUNCATE = 0
ASSETS = []
HAS_STATIC = False
HAS_MAIN = False
LEVEL = -1
PNGOPT = []


def pack_files(zf, parent, zfolders, newpath):
    global COUNTER, TRUNCATE, ASSETS, HAS_STATIC, HAS_MAIN, LEVEL, PNGOPT
    try:
        LEVEL += 1
        os.chdir(newpath)

        for current, dirnames, filenames in os.walk(newpath):
            p_dirname = Path(current)
            dispname = Path(current[TRUNCATE:] or "/").as_posix()
            print(
                f"now in .{dispname} [lvl={LEVEL} dirs={len(dirnames)} files={len(filenames)}]"
            )

            for subdir in dirnames:

                # do not put git subfolders
                if subdir.startswith(".git"):
                    continue

                # do not put python build/cache folders
                if subdir in ["build", "__pycache__"]:
                    continue

                # do not archive static web files at toplevel
                if LEVEL == 0:
                    if subdir == "static":
                        HAS_STATIC = True
                        continue

                # recurse
                zfolders.append(subdir)
                pack_files(
                    zf, p_dirname, zfolders, p_dirname.joinpath(subdir).as_posix()
                )

            for f in filenames:
                # do not pack ourself
                if f.endswith(".apk"):
                    continue

                # skip pngquant optimized cache files
                if f.endswith("-pygbag.png"):
                    continue

                if f.endswith(".gitignore"):
                    continue

                if Path(f).is_symlink():
                    print("sym", f)

                if not os.path.isfile(f):
                    continue

                if LEVEL == 0 and f == "main.py":
                    HAS_MAIN = True

                # folders to skip __pycache__
                # extensions to skip : pyc pyx pyd pyi
                zpath = list(zfolders)
                zpath.append(f)
                src = "/".join(zpath)

                ext = f.rsplit(".", 1)[-1].lower()
                if ext == "wav":
                    print(
                        """
    ===============================================================
        using .wav format for in assets for web publication
        has a serious performance/size hit, prefer .ogg format
    ===============================================================
"""
                    )
                if ext == "png":
                    name, ext = f.rsplit(".", 1)
                    maybe = f"{name}-pygbag.png"
                    if Path(maybe).is_file():
                        PNGOPT.append(f)
                        f = maybe

                if not src in ASSETS:
                    # print( zpath , f )
                    zf.write(f, src)
                    ASSETS.append(src)

                    COUNTER += 1

            break

    finally:
        os.chdir(parent)
        zfolders.pop()
        LEVEL -= 1


def archive(apkname, target_folder, build_dir=None):
    global COUNTER, TRUNCATE, ASSETS, HAS_MAIN, HAS_STATIC
    TRUNCATE = len(target_folder.as_posix())
    if build_dir:
        apkname = build_dir.joinpath(apkname).as_posix()

    try:
        with zipfile.ZipFile(
            apkname, mode="x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zf:
            pack_files(zf, Path.cwd(), ["assets"], target_folder)
    except TypeError:
        # 3.6 does not support compresslevel
        with zipfile.ZipFile(apkname, mode="x", compression=zipfile.ZIP_DEFLATED) as zf:
            pack_files(zf, Path.cwd(), ["assets"], target_folder)
    print(COUNTER)

    if not (HAS_MAIN or HAS_STATIC):
        print("Warning : this apk has no startup file (main.py or static )")

    if len(PNGOPT):
        print(f"INFO: {len(PNGOPT)} png format files were optimized for packing")


def web_archive(apkname, build_dir):
    archfile = build_dir.with_name("web.zip")
    if archfile.is_file():
        archfile.unlink()

    with zipfile.ZipFile(archfile, mode="x", compression=zipfile.ZIP_STORED) as zf:
        for f in ("index.html", "favicon.png", apkname):
            zf.write(build_dir.joinpath(f), f)
