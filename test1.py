import sys
from bandit.cli.main import main

if __name__ == "__main__":
    sys.argv = [
        "bandit",
        "-r",
        "main.py",            # 可以是文件或文件夹
        "-f",
        "txt",                # 注意这里是 txt，不是 text
        "-o",
        "bandit_report.txt"
    ]
    main()
