# Repo2PDF

## Overview
This tool was inspired by [repo2pdf](https://github.com/BankkRoll/repo2pdf?tab=MIT-1-ov-file).

Repo2PDF is a Python tool that converts source code repositories into a well-formatted PDF. It supports repositories from GitHub, local directories, and ZIP files containing source code. The tool automatically installs `wkhtmltopdf` if needed, formats code using syntax highlighting, and excludes specified files based on a `repo2pdf.ignore` configuration.

## Features
- Clone a GitHub repository and generate a PDF of its source code.
- Process a local directory containing source files.
- Extract and process a ZIP file containing a repository.
- Syntax highlighting using `pygments`.
- Ignore unwanted files based on a configuration file.
- Automatic `wkhtmltopdf` installation if missing.
- Handles read-only files and directory cleanup automatically.

## Installation

### Requirements
Ensure you have Python installed on your system. Then install the required dependencies:

```sh
pip install -r requirements.txt
```

## Usage
Run the script and provide a repository URL, local directory, or ZIP file when prompted:

```sh
python main.py
```

You will be asked to enter:
- A **GitHub repository URL** (e.g., `https://github.com/user/repo`)
- A **local directory** path
- A **ZIP file** containing a repository

The script will process the files, apply syntax highlighting, and generate a PDF with the same name as the repository, directory, or ZIP file.

## Ignoring Files
You can specify files and extensions to exclude by creating a `repo2pdf.ignore` file in the repository root:

```json
{
  "ignoredFiles": [
    "README.md",
    "LICENSE"
  ],
  "ignoredExtensions": [
    ".log",
    ".png",
    ".jpg"
  ]
}
```

## Example Output
If you process `my-repo`, the resulting file will be:

```
my-repo.pdf
```

## License
This project is licensed under the MIT License.

