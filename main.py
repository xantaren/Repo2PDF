import os
import json
import shutil
import pdfkit
import subprocess
import platform
import stat
import zipfile


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
    """Processes source files and generates a PDF with minimal spacing."""
    wkhtmltopdf_path = get_wkhtmltopdf_path()

    # CSS with minimal spacing
    css = """
        pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            margin: 0;
            font-family: 'Courier New', monospace;
            counter-reset: line;
            line-height: 1.4;
            font-size: 11px;
            background-color: #f8f8f8;
            padding: 5px 0;
        }
        code {
            display: block;
            padding-left: 50px;
            position: relative;
        }
        code > span {
            display: block;
            padding: 0 5px 0 0;
            min-height: 1.4em;
        }
        code > span:before {
            counter-increment: line;
            content: counter(line);
            position: absolute;
            left: 0;
            width: 35px;
            text-align: right;
            color: #666;
            border-right: 1px solid #ddd;
            padding-right: 8px;
            font-size: 11px;
        }
        .file-header {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            padding: 5px 8px;
            margin: 0;
            background-color: #f1f1f1;
            font-size: 14px;
            color: #333;
        }
        hr {
            margin: 10px 0;
            border: none;
            border-top: 1px solid #ddd;
        }
    """

    html_content = f"""
    <html>
    <head>
        <style>{css}</style>
    </head>
    <body style="margin:0;padding:0;">
    """

    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            if should_exclude(repo_path, file_path, ignore_config):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()

                code_html = ""
                for line in code.split('\n'):
                    line = (line.replace('&', '&amp;')
                            .replace('<', '&lt;')
                            .replace('>', '&gt;')
                            .replace('"', '&quot;')
                            .replace("'", '&#39;'))
                    code_html += f"<span>{line}</span>"

                relative_path = os.path.relpath(file_path, repo_path)
                html_content += f"""
                    <div class="file-header">{relative_path}</div>
                    <pre><code>{code_html}</code></pre>
                    <hr>
                """
            except Exception as e:
                print(f"Skipping {file}: {e}")

    html_content += "</body></html>"

    # Minimal margins in PDF options
    options = {
        'encoding': 'UTF-8',
        'quiet': '',
        'margin-top': '2mm',
        'margin-right': '2mm',
        'margin-bottom': '2mm',
        'margin-left': '2mm',
        'page-size': 'A4'
    }

    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
    pdfkit.from_string(html_content, output_file, configuration=config, options=options)
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
