@echo off
setlocal

rem Path to the venv python
set PYVENV=%~dp0\.venv\Scripts\python.exe

if not exist "%PYVENV%" (
  echo ERROR: Python in venv not found at %PYVENV%
  echo Ensure the backend virtualenv exists at backend\.venv
  exit /b 1
)

echo Using Python: %PYVENV%

echo Upgrading pip, setuptools, wheel...
%PYVENV% -m pip install --upgrade pip setuptools wheel

echo Uninstalling bcrypt and passlib (if present)...
%PYVENV% -m pip uninstall -y bcrypt passlib

echo Installing bcrypt and passlib with bcrypt backend...
%PYVENV% -m pip install --no-cache-dir --force-reinstall bcrypt==4.0.1
%PYVENV% -m pip install --no-cache-dir --force-reinstall "passlib[bcrypt]"

echo Verifying bcrypt and passlib installation:
%PYVENV% -c "import bcrypt,passlib; print('bcrypt.__about__=', getattr(bcrypt,'__about__',None)); print('bcrypt.__file__=', bcrypt.__file__); print('passlib.__version__=', passlib.__version__)"

echo Running password checks for users:
%PYVENV% backend\scripts\check_login.py uday@gmail.com Uday@324
%PYVENV% backend\scripts\check_login.py Harish@gmail.com Harish@123

echo Done.
endlocal
