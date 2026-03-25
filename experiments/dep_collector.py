import os

directory = "Main FIle"
dep_path = []

for root, _, files in os.walk(directory):
    if "requirements.txt" in files:
        dep_path.append(root)


final_paths = []

for d in dep_path:
    final_paths.append(os.path.join(d, "requirements.txt"))

dep = []

for path in final_paths:
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Extract the bare package name (before any version specifier)
            pkg_name = line.split("~=")[0].split("==")[0].split(">=")[0].split("<=")[
                0].split("!=")[0].split(">")[0].split("<")[0].split("[")[0].strip().lower()
            dep.append(pkg_name)


with open("requirements.txt", "w") as f:
    for i in dep:
        f.write(f"{i}\n")
