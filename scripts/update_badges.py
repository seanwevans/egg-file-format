import re
import xml.etree.ElementTree as ET
from pathlib import Path

README_PATH = Path("README.md")
COVERAGE_XML = Path("coverage.xml")
PYLINT_LOG = Path("pylint.log")


def update_coverage(readme_text: str) -> str:
    if not COVERAGE_XML.exists():
        return readme_text
    root = ET.parse(COVERAGE_XML).getroot()
    line_rate = float(root.get("line-rate", 0))
    percent = round(line_rate * 100)
    pattern = re.compile(r"(https://img.shields.io/badge/coverage-)(\d+)%25-(\w+)")

    def repl(match: re.Match) -> str:
        return f"{match.group(1)}{percent}%25-{match.group(3)}"

    return pattern.sub(repl, readme_text)


def update_pylint(readme_text: str) -> str:
    if not PYLINT_LOG.exists():
        return readme_text
    rating = None
    for line in PYLINT_LOG.read_text().splitlines():
        if "Your code has been rated at" in line:
            m = re.search(r"rated at ([0-9.]+)/10", line)
            if m:
                rating = float(m.group(1))
    if rating is None:
        return readme_text
    rating_str = f"{rating:.2f}/10"
    rating_url = rating_str.replace("/", "%2F")
    pattern = re.compile(r"(https://img.shields.io/badge/pylint-)[0-9.]+%2F10-(\w+)")
    return pattern.sub(lambda m: f"{m.group(1)}{rating_url}-{m.group(2)}", readme_text)


def main() -> None:
    text = README_PATH.read_text()
    text = update_coverage(text)
    text = update_pylint(text)
    README_PATH.write_text(text)


if __name__ == "__main__":
    main()
