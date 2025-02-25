# Repo2PDF

## Overview
Repo2PDF is a Python tool that converts source code repositories into a well-formatted PDF. It supports repositories from GitHub, local directories, and ZIP files containing source code. The tool automatically installs `wkhtmltopdf` if needed, formats code, and excludes specified files based on a configuration file.

I built this because I needed an easy way to share my entire codebase with common LLM solutions, which often support PDFs but lack mass or codebase upload features.

This tool was inspired by [repo2pdf](https://github.com/BankkRoll/repo2pdf).

## Features
- Clone a GitHub repository and generate a PDF of its source code
- Process a local directory containing source files
- Extract and process a ZIP file containing a repository
- Ignore unwanted files based on a configuration file
- Automatic `wkhtmltopdf` installation if missing
- **Batch processing for handling gigantic monorepos**
- **Parallel file processing for improved performance**
- **Smart file filtering to exclude binary and large files**
- **Memory-efficient processing to prevent freezing with large repositories**

## Installation

### Requirements
Ensure you have Python installed on your system. Then install the required dependencies:

```sh
pip install -r requirements.txt
```

### Optional Dependencies
For optimal PDF merging performance with large repositories:

```sh
pip install PyPDF2
```

Alternatively, you can install `pdftk` on your system:
- Ubuntu/Debian: `sudo apt install pdftk`
- macOS: `brew install pdftk-java`

## Usage
Run the script and provide a repository URL, local directory, or ZIP file:

```sh
python3 main.py <repository_path> [options]
```

### Options
- `--prettify`: Generate a PDF with enhanced formatting (line numbers, syntax highlighting)
- `--output FILENAME`: Specify the output PDF filename (default: based on repository name)
- `--max-size SIZE`: Maximum file size in KB to include (default: 500)
- `--batch-size SIZE`: Maximum files per batch (default: 100)
- `--shallow-clone`: Use shallow clone for git repositories (faster for large repos)
- `--verbose`: Enable detailed logging

### Examples
To generate a basic PDF from a GitHub repository:
```sh
python3 main.py https://github.com/user/repo
```

To generate a pretty PDF with enhanced formatting:
```sh
python3 main.py https://github.com/user/repo --prettify
```

To process a large repository with optimized settings:
```sh
python3 main.py https://github.com/user/large-repo --shallow-clone --batch-size 50 --max-size 200
```

## Ignoring Files
You can specify files and extensions to exclude by creating an `ignore.json` file in the current directory:

```json
{
  "ignoredFiles": [
    ".gitignore",
    "README.md",
    "LICENSE"
  ],
  "ignoredExtensions": [
    ".log",
    ".png",
    ".jpg",
    ".zip",
    ".tar.gz"
  ],
  "ignoredPaths": [
    ".git",
    "node_modules",
    "dist",
    "build"
  ],
  "maxFileSizeKB": 500,
  "maxFilesPerBatch": 100
}
```

### Default Ignored Items
By default, the tool ignores:
- Common binary files (images, videos, archives)
- Common large directories (.git, node_modules, __pycache__, etc.)
- Files larger than 500KB
- Files that appear to be binary (contain null bytes)

## Example Output
If you process `my-repo`, the resulting file will be:

```
my-repo.pdf
```

## Troubleshooting

### Memory Issues with Large Repositories
If you're still experiencing issues with very large repositories:

1. Use the `--shallow-clone` option to only fetch the latest version of files
2. Reduce batch size with `--batch-size 20` (or even lower)
3. Lower the maximum file size with `--max-size 100`
4. Install PyPDF2 for more efficient PDF merging
5. Add more directories to the ignore list in your `ignore.json`

### PDF Merging Failures
- Install PyPDF2: `pip install PyPDF2`
- If PyPDF2 is unavailable, install pdftk on your system

## License
This project is licensed under the MIT License.