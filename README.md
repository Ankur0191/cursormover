# CursorMover

A small Windows utility that makes occasional, bounded, non-linear cursor movements.

## Features
- Adjustable movement interval (1–60 seconds; default 5 seconds)
- Adjustable movement radius (default 35 px)
- Smooth, curved movement paths
- Start / Stop controls and a visible status indicator
- Pauses when real user input is detected
- Stops automatically when the app exits

## Build on Windows
1. Install Python 3.11+.
2. Open PowerShell in this folder.
3. Run `python -m pip install -r requirements.txt`.
4. Run `python -m PyInstaller --noconfirm --clean --onefile --windowed --name CursorMover --collect-all customtkinter main.py`.
5. Find the executable at `dist\CursorMover.exe`.

Or download the **CursorMover Windows EXE** artifact from the GitHub Actions run after pushing to `main`.

## Run from source
```powershell
python -m pip install -r requirements.txt
python main.py
```

## Notes
CursorMover moves the real Windows pointer. It is not a guarantee that another application will register activity or treat the user as present. Use it only where permitted. The app deliberately pauses after detected human keyboard/mouse input to avoid fighting the user for control.
