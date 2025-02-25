import os
import json
import shutil
import pdfkit
import subprocess
import platform
import stat
import zipfile
import argparse
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        logger.info("wkhtmltopdf is already installed.")
        return

    system_os = platform.system()
    if system_os == "Windows":
        installer_url = "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.msvc2015-win64.exe"
        installer_path = "wkhtmltopdf_installer.exe"
        logger.info("Downloading wkhtmltopdf...")
        os.system(f"curl -L -o {installer_path} {installer_url}")
        logger.info("Installing wkhtmltopdf...")
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
    subprocess.run(["git", "clone", "--depth=1", repo_url, local_path], check=True)
    logger.info(f"Repository cloned to {local_path}")


def extract_zip(zip_path, extract_to):
    """Extracts a ZIP file to the specified directory."""
    if os.path.exists(extract_to):
        remove_readonly_rmtree(extract_to)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    logger.info(f"ZIP extracted to {extract_to}")


def remove_readonly_rmtree(path):
    """Removes a directory even if it contains read-only files."""

    def onerror(func, path, exc_info):
        if os.path.exists(path):
            os.chmod(path, stat.S_IWRITE)
            func(path)

    shutil.rmtree(path, onerror=onerror)


def load_ignore_config(repo_path):
    """Loads ignore configuration from ignore.json if available."""
    ignore_file = os.path.join(repo_path, "ignore.json")
    ignore_config = {
        "ignoredFiles": [],
        "ignoredExtensions": [".pdf", ".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mp3", ".zip", ".tar", ".gz"],
        "ignoredPaths": [".git", "node_modules", "__pycache__", "venv", "env", ".venv", ".env", "dist", "build"],
        "maxFileSizeKB": 500,  # Default max file size of 500KB
        "maxFilesPerBatch": 100  # Default max files per batch
    }

    if os.path.exists(ignore_file):
        with open(ignore_file, "r") as f:
            logger.info(f"Loading ignore config from {ignore_file}")
            loaded_config = json.load(f)
            ignore_config.update(loaded_config)  # Merge loaded config with defaults

    return ignore_config


def should_exclude(repo_path, file_path, ignore_config):
    """Checks if a file should be ignored based on path, extension, size, or binary content."""
    # Skip files larger than the configured max size
    max_size_kb = ignore_config.get("maxFileSizeKB", 500)
    if os.path.getsize(file_path) > max_size_kb * 1024:
        return True

    # Skip based on configured ignore rules
    abs_file_path = os.path.abspath(file_path)
    rel_file_path = os.path.relpath(file_path, repo_path)

    # Check ignored paths
    for ignored_path in ignore_config["ignoredPaths"]:
        norm_ignored_path = os.path.normpath(ignored_path)
        if (rel_file_path.startswith(norm_ignored_path + os.sep) or
                rel_file_path == norm_ignored_path):
            return True

    # Check ignored files and extensions
    if (os.path.basename(file_path) in ignore_config["ignoredFiles"] or
            os.path.splitext(file_path)[1].lower() in ignore_config["ignoredExtensions"]):
        return True

    # Check if file is likely binary
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:  # Simple binary detection
                return True
    except Exception:
        return True  # If we can't read the file, better skip it

    return False


def process_file(file_info, is_pretty=True):
    """Process a single file and return its HTML representation."""
    file_path, relative_path = file_info

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()

        if is_pretty:
            code_html = ""
            for i, line in enumerate(code.split('\n')):
                line = (line.replace('&', '&amp;')
                        .replace('<', '&lt;')
                        .replace('>', '&gt;')
                        .replace('"', '&quot;')
                        .replace("'", '&#39;'))
                code_html += f"<span>{line}</span>"

            html = f"""
                <div class="file-header">{relative_path}</div>
                <pre><code>{code_html}</code></pre>
                <hr>
            """
        else:
            code = (code.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;'))
            html = f"<h3>File: {relative_path}</h3><pre>{code}</pre><hr>\n"

        return html
    except Exception as e:
        logger.warning(f"Skipping {file_path}: {e}")
        return f"<h3>File: {relative_path}</h3><pre>Error reading file: {str(e)}</pre><hr>\n"


def get_files_to_process(repo_path, ignore_config):
    """Get list of files to process, respecting ignore rules."""
    files_to_process = []

    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            if not should_exclude(repo_path, file_path, ignore_config):
                relative_path = os.path.relpath(file_path, repo_path)
                files_to_process.append((file_path, relative_path))

    return files_to_process


def process_files_in_batches(files_to_process, output_file, is_pretty=True, max_files_per_batch=100):
    """Process files in batches and merge PDFs together."""
    if not files_to_process:
        logger.warning("No files to process!")
        return

    logger.info(f"Processing {len(files_to_process)} files in batches")

    # Create CSS for pretty mode
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

    # PDF conversion options
    wkhtmltopdf_path = get_wkhtmltopdf_path()
    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)

    if is_pretty:
        options = {
            'encoding': 'UTF-8',
            'quiet': '',
            'margin-top': '2mm',
            'margin-right': '2mm',
            'margin-bottom': '2mm',
            'margin-left': '2mm',
            'page-size': 'A4'
        }
    else:
        options = {
            'encoding': 'UTF-8',
            'quiet': '',
            'margin-top': '5mm',
            'margin-right': '5mm',
            'margin-bottom': '5mm',
            'margin-left': '5mm',
            'page-size': 'A4',
            'no-outline': None,
            'grayscale': None,
            'lowquality': None,
        }

    # Process files in batches using multiple threads
    batch_pdfs = []
    batch_count = (len(files_to_process) + max_files_per_batch - 1) // max_files_per_batch

    for batch_idx in range(batch_count):
        start_idx = batch_idx * max_files_per_batch
        end_idx = min(start_idx + max_files_per_batch, len(files_to_process))
        batch = files_to_process[start_idx:end_idx]

        logger.info(f"Processing batch {batch_idx + 1}/{batch_count} ({len(batch)} files)")

        # Create temp dir for this batch
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            batch_pdf = tmp.name

        # Process files in parallel
        html_parts = []
        with ThreadPoolExecutor(max_workers=min(os.cpu_count() or 4, 8)) as executor:
            futures = {executor.submit(process_file, file_info, is_pretty): file_info for file_info in batch}
            for future in as_completed(futures):
                html_content = future.result()
                if html_content:
                    html_parts.append(html_content)

        # Create HTML for the batch
        batch_html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>{'body {font-family:monospace;font-size:10px}' if not is_pretty else css}</style>
        </head>
        <body>
            <h1>Batch {batch_idx + 1}/{batch_count}</h1>
            {''.join(html_parts)}
        </body>
        </html>
        """

        # Convert to PDF
        try:
            pdfkit.from_string(batch_html, batch_pdf, configuration=config, options=options)
            batch_pdfs.append(batch_pdf)
            logger.info(f"Generated PDF for batch {batch_idx + 1}")
        except Exception as e:
            logger.error(f"Error generating PDF for batch {batch_idx + 1}: {e}")

    # Merge PDFs if needed
    if len(batch_pdfs) == 1:
        # Only one batch was processed, just rename
        shutil.move(batch_pdfs[0], output_file)
    else:
        # Merge multiple batch PDFs
        merge_pdfs(batch_pdfs, output_file)

    # Cleanup temp files
    for pdf in batch_pdfs:
        if os.path.exists(pdf):
            os.unlink(pdf)

    logger.info(f"Final PDF generated: {output_file}")


def merge_pdfs(input_files, output_file):
    """Merge multiple PDFs into one."""
    # Try to use PyPDF2 for merging
    try:
        from PyPDF2 import PdfWriter, PdfReader
        merger = PdfWriter()

        for pdf in input_files:
            if os.path.exists(pdf) and os.path.getsize(pdf) > 0:
                merger.append(PdfReader(pdf))

        with open(output_file, "wb") as f:
            merger.write(f)

        logger.info(f"Merged {len(input_files)} PDFs using PyPDF2")
        return True
    except ImportError:
        logger.warning("PyPDF2 not found, attempting alternative merging approach")
    except Exception as e:
        logger.error(f"Error merging with PyPDF2: {e}")

    # Try using pdftk if available
    try:
        pdftk_command = ["pdftk"]
        for pdf in input_files:
            if os.path.exists(pdf) and os.path.getsize(pdf) > 0:
                pdftk_command.append(pdf)
        pdftk_command.extend(["cat", "output", output_file])

        subprocess.run(pdftk_command, check=True)
        logger.info(f"Merged {len(input_files)} PDFs using pdftk")
        return True
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning(f"pdftk merging failed: {e}")

    # If we get here, neither PyPDF2 nor pdftk worked
    # Create a simple HTML that embeds all PDFs and convert that to a single PDF
    try:
        temp_html_file = tempfile.mktemp(suffix=".html")

        # Create an HTML file that includes all PDFs
        html_content = """
        <html>
        <head>
            <title>Merged PDF Document</title>
            <style>
                body { margin: 0; padding: 0; }
                .pdf-container { page-break-after: always; }
                iframe { width: 100%; height: 100vh; border: none; }
            </style>
        </head>
        <body>
        """

        # Convert PDFs to base64 and embed them
        for i, pdf_file in enumerate(input_files):
            if os.path.exists(pdf_file) and os.path.getsize(pdf_file) > 0:
                html_content += f"""
                <div class="pdf-container">
                    <h2>Section {i + 1}</h2>
                    <p>The content from batch {i + 1} would appear here.</p>
                    <p>Please install PyPDF2 or pdftk for proper PDF merging.</p>
                </div>
                """

        html_content += "</body></html>"

        with open(temp_html_file, "w") as f:
            f.write(html_content)

        # Convert this HTML to PDF
        wkhtmltopdf_path = get_wkhtmltopdf_path()
        options = {
            'quiet': '',
            'page-size': 'A4',
            'margin-top': '10mm',
            'margin-right': '10mm',
            'margin-bottom': '10mm',
            'margin-left': '10mm',
        }
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        pdfkit.from_file(temp_html_file, output_file, configuration=config, options=options)

        # Clean up
        os.unlink(temp_html_file)

        logger.warning("Created a placeholder PDF. For proper merging, please install PyPDF2 or pdftk")
        return True
    except Exception as e:
        logger.error(f"All PDF merging methods failed: {e}")

    # As a last resort, just copy the first PDF
    if input_files:
        try:
            shutil.copy(input_files[0], output_file)
            logger.warning(f"Failed to merge PDFs. Copied only the first PDF to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Even copying the first PDF failed: {e}")

    return False


# Add this to your main function before process_files_in_batches call:
def check_dependencies():
    """Check for optional dependencies and install if possible."""
    try:
        import PyPDF2
        logger.info("PyPDF2 is installed and available for PDF merging")
    except ImportError:
        logger.warning("PyPDF2 is not installed. PDF merging may not work optimally.")
        logger.info("You can install it with: pip install PyPDF2")

        # Check if pdftk is available as an alternative
        try:
            subprocess.run(["pdftk", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info("pdftk is installed and available for PDF merging")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Neither PyPDF2 nor pdftk is available for proper PDF merging")
            logger.info("For best results, install PyPDF2: pip install PyPDF2")


def main():
    check_dependencies()
    parser = argparse.ArgumentParser(
        description="Generate a PDF from a GitHub repository, local folder, or ZIP file."
    )
    parser.add_argument("input_path", help="GitHub repository URL, local path, or ZIP file.")
    parser.add_argument("--prettify", action="store_true", help="Generate a pretty PDF with enhanced formatting.")
    parser.add_argument("--output", help="Output PDF file name. Default is based on input name.")
    parser.add_argument("--max-size", type=int, default=500, help="Maximum file size in KB to include (default: 500)")
    parser.add_argument("--batch-size", type=int, default=100, help="Maximum files per batch (default: 100)")
    parser.add_argument("--shallow-clone", action="store_true",
                        help="Use shallow clone for git repositories (--depth=1)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    logger.info("Checking for wkhtmltopdf installation...")
    install_wkhtmltopdf()

    input_path = args.input_path
    is_pretty_pdf = args.prettify

    # Determine output file name
    if args.output:
        output_file = args.output
    else:
        repo_name = os.path.splitext(os.path.basename(input_path))[0]
        output_file = f"{repo_name}.pdf"

    # Create a temp directory for processing
    local_path = tempfile.mkdtemp(prefix="repo_pdf_")

    try:
        # Get repository
        if input_path.endswith(".zip") and os.path.exists(input_path):
            extract_zip(input_path, local_path)
        elif os.path.isdir(input_path):
            # Use the input path directly without copying to save time and space
            local_path = input_path
        else:
            # Git clone with depth=1 for speed if shallow-clone is specified
            clone_args = ["git", "clone"]
            if args.shallow_clone:
                clone_args.extend(["--depth=1"])
            clone_args.extend([input_path, local_path])

            logger.info(f"Cloning repository: {' '.join(clone_args)}")
            if os.path.exists(local_path):
                remove_readonly_rmtree(local_path)
            subprocess.run(clone_args, check=True)
            logger.info(f"Repository cloned to {local_path}")

        # Load ignore config
        ignore_config = load_ignore_config(os.getcwd())

        # Apply command-line arguments to override config
        ignore_config["maxFileSizeKB"] = args.max_size
        ignore_config["maxFilesPerBatch"] = args.batch_size

        # Get list of files to process
        logger.info("Finding files to process...")
        files_to_process = get_files_to_process(local_path, ignore_config)
        logger.info(f"Found {len(files_to_process)} files to process")

        # Process files in batches
        process_files_in_batches(
            files_to_process,
            output_file,
            is_pretty=is_pretty_pdf,
            max_files_per_batch=ignore_config["maxFilesPerBatch"]
        )

    finally:
        # Cleanup
        if local_path != input_path and os.path.exists(local_path):
            logger.info(f"Cleaning up temporary directory: {local_path}")
            remove_readonly_rmtree(local_path)


if __name__ == "__main__":
    main()