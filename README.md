# Repo2PDF

## Overview
Repo2PDF is a Python tool that converts source code repositories into a well-formatted PDF. It supports repositories from GitHub, local directories, and ZIP files containing source code. The tool automatically installs `wkhtmltopdf` if needed, formats code, and excludes specified files based on a `ignore.json` configuration.

I built this because I needed an easy way to share my entire codebase with common LLM solutions, which often support PDFs but lack mass or codebase upload features.

This tool was inspired by [repo2pdf](https://github.com/BankkRoll/repo2pdf).

## Features
- Clone a GitHub repository and generate a PDF of its source code.
- Process a local directory containing source files.
- Extract and process a ZIP file containing a repository.
- Ignore unwanted files based on a configuration file.
- Automatic `wkhtmltopdf` installation if missing.

## Installation

### Requirements
Ensure you have Python installed on your system. Then install the required dependencies:

```sh
pip install -r requirements.txt
```

## Usage
Run the script and provide a repository URL, local directory, or ZIP file when prompted:

```sh
python3 main.py <repository_path> [--prettify]
```
For example:
To generate a PDF with basic formatting:

```sh
python3 main.py https://github.com/user/repo
```
To generate a PDF with enhanced (pretty) formatting:
```sh
python3 main.py https://github.com/user/repo --prettify
```

## Ignoring Files
You can specify files and extensions to exclude by creating a `repo2pdf.ignore` file in the repository root:

```json
{
  "ignoredFiles": [
    ".gitignore"
  ],
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

