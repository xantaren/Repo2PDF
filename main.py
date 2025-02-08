import os
import json
import shutil
import pygments
import pdfkit
import subprocess
import platform
import stat
import zipfile
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter


def is_wkhtmltopdf_installed():
    """Checks if wkhtmltopdf is installed."""
    system_os = platform.system()
    if system_os == "Windows":
        return os.path.exists("C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
    try:
        result = subprocess.run(["which", "wkhtmltopdf"], capture_output=True, text=True)
        return bool(result.stdout.strip())
    except FileNotFoundError:
        return False


def install_wkhtmltopdf():
    """Ensures wkhtmltopdf is installed if missing."""
    if is_wkhtmltopdf_installed():
        print("wkhtmltopdf is already installed.")
        return

    system_os = platform.system()
    if system_os == "Windows":
        installer_url = "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.msvc2015-win64.exe"
        installer_path = "wkhtmltopdf_installer.exe"
        print("Downloading wkhtmltopdf...")
        os.system(f"curl -L -o {installer_path} {installer_url}")
        print("Installing wkhtmltopdf...")
        os.system(f"{installer_path} /S")
        os.remove(installer_path)
    elif system_os == "Linux":
        os.system("sudo apt update && sudo apt install -y wkhtmltopdf")
    elif system_os == "Darwin":
        os.system("brew install wkhtmltopdf")


def get_wkhtmltopdf_path():
    """Finds the installed path of wkhtmltopdf."""
    if platform.system() == "Windows":
        return "C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"
    try:
        result = subprocess.run(["which", "wkhtmltopdf"], capture_output=True, text=True)
        path = result.stdout.strip()
        if path:
            return path
    except FileNotFoundError:
        pass

    return "wkhtmltopdf"


def clone_repo(repo_url, local_path):
    """Clones a repository to the specified local path using subprocess."""
    if os.path.exists(local_path):
        remove_readonly_rmtree(local_path)
    subprocess.run(["git", "clone", repo_url, local_path], check=True)
    print(f"Repository cloned to {local_path}")


def extract_zip(zip_path, extract_to):
    """Extracts a ZIP file to the specified directory."""
    if os.path.exists(extract_to):
        remove_readonly_rmtree(extract_to)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"ZIP extracted to {extract_to}")


def remove_readonly_rmtree(path):
    """Removes a directory even if it contains read-only files."""

    def onerror(func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(path, onerror=onerror)


def load_ignore_config(repo_path):
    """Loads ignore configuration from ignore.json if available."""
    ignore_file = os.path.join(repo_path, "ignore.json")
    ignore_config = {"ignoredFiles": [], "ignoredExtensions": [], "ignoredPaths": []}

    if os.path.exists(ignore_file):
        with open(ignore_file, "r") as f:
            print(ignore_file)
            loaded_config = json.load(f)
            ignore_config.update(loaded_config)  # Merge loaded config with defaults

    return ignore_config


def should_exclude(repo_path, file_path, ignore_config):
    """Checks if a file should be ignored."""
    abs_file_path = os.path.abspath(file_path)
    for ignored_path in ignore_config["ignoredPaths"]:
        abs_ignored_path = os.path.abspath(os.path.join(repo_path, ignored_path))
        if abs_file_path.startswith(abs_ignored_path):
            print(f"Excluding {file_path} based on ignore rules.")
            return True
    if (os.path.basename(file_path) in ignore_config["ignoredFiles"]
            or os.path.splitext(file_path)[1] in ignore_config["ignoredExtensions"]):
        print(f"Excluding {file_path} based on ignore rules.")
        return True
    return False


def generate_pdf(repo_path, output_file, ignore_config):
    """Processes source files and generates a PDF."""
    wkhtmltopdf_path = get_wkhtmltopdf_path()

    html_content = """<html><body>"""
    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            if should_exclude(repo_path, file_path, ignore_config):
                continue

            try:
                ext = os.path.splitext(file)[1][1:]
                lexer = get_lexer_by_name(ext) if ext else get_lexer_by_name("text")
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                formatted_code = pygments.highlight(code, lexer, HtmlFormatter())
                html_content += f"<h2>{file}</h2>{formatted_code}<hr>"
            except Exception as e:
                print(f"Skipping {file}: {e}")

    html_content += "</body></html>"
    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
    pdfkit.from_string(html_content, output_file, configuration=config)
    print(f"PDF generated: {output_file}")


def main():
    print("Checking for wkhtmltopdf installation...")
    install_wkhtmltopdf()

    input_path = input("Enter a GitHub repository URL, a local path, or a zip file: ")
    local_path = "./temp_repo"
    repo_name = os.path.splitext(os.path.basename(input_path))[0]
    output_file = f"{repo_name}.pdf"

    if input_path.endswith(".zip") and os.path.exists(input_path):
        extract_zip(input_path, local_path)
    elif os.path.isdir(input_path):
        local_path = input_path
    else:
        clone_repo(input_path, local_path)

    ignore_config = load_ignore_config(os.getcwd())
    generate_pdf(local_path, output_file, ignore_config)

    if input_path.endswith(".zip") or not os.path.isdir(input_path):
        remove_readonly_rmtree(local_path)  # Cleanup
        print("Temporary repo deleted.")


if __name__ == "__main__":
    main()
