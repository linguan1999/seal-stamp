#!/usr/bin/env python3
"""macOS 用 Pages 将 .doc/.docx 转为 PDF。首次运行需允许自动化权限。
用法: doc2pdf.py input.doc output.pdf"""
import subprocess
import sys

SCRIPT = '''
on run argv
	set inFile to POSIX file (item 1 of argv)
	set outFile to POSIX file (item 2 of argv)
	tell application "Pages"
		launch
		open inFile
		delay 3
		set theDoc to front document
		export theDoc as PDF to outFile
		close theDoc saving no
	end tell
end run
'''


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: doc2pdf.py input.doc output.pdf")
    r = subprocess.run(["osascript", "-e", SCRIPT, sys.argv[1], sys.argv[2]])
    raise SystemExit(r.returncode)


if __name__ == "__main__":
    main()
