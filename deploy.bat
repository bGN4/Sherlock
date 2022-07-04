CD /D %~dp0
py.exe -3 -m venv env
env\Scripts\python.exe -m pip install -r requirements.txt
