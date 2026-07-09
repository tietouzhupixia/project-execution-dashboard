# Python Environment

Use the local virtual environment in this project.

Project root:

```text
D:\英大碳资产实习\进度信息表\streamlit_project_dashboard
```

Python executable:

```text
D:\英大碳资产实习\进度信息表\streamlit_project_dashboard\.venv\Scripts\python.exe
```

Streamlit executable:

```text
D:\英大碳资产实习\进度信息表\streamlit_project_dashboard\.venv\Scripts\streamlit.exe
```

## Installed

The environment has already been created and dependencies have been installed from `requirements.txt`.

Verified:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\streamlit.exe --version
```

Result at setup time:

```text
2 passed
Streamlit, version 1.59.0
```

## Run App

Preferred:

```powershell
.\run_streamlit.ps1
```

Equivalent direct command:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

## Rebuild Environment

Only if `.venv` is missing or broken:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Important for future AI:

- Do not use the system Python for tests or running the app.
- Always use `.venv\Scripts\python.exe` and `.venv\Scripts\streamlit.exe`.
- `requirements.txt` = runtime deps only (used by Streamlit Cloud deploys);
  `requirements-dev.txt` adds pytest/playwright for local dev. Install dev.
- If adding packages, install them into `.venv` and update the right file.

