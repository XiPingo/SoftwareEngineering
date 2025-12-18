from pylint.lint import Run
from pylint.reporters.text import TextReporter

if __name__ == "__main__":
    with open("pylint_report.txt", "w") as f:
        reporter = TextReporter(output=f)
        Run(["main.py"], reporter=reporter, exit=False)


