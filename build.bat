pip install pyinstaller
if not errorlevel 0 exit

set install_requirements=pip install -r script.requirements.txt
set arguments=--specpath dist --onefile --version-file=..\script.txt --icon=..\MM.ico script.pyw  --add-data "..\MM.ico;."


REM %install_requirements:script=MUA_ColorConverter%
pyinstaller %arguments:script=MUA_ColorConverter% --add-data "..\tkBreeze;tkBreeze"


REM ----------------- CustomTkInter Variant --------------------

for /f "tokens=1* delims=: " %%k in ('pip show customtkinter ^| findstr /bl "Location"') do set l=%%l
if not errorlevel 0 exit

%install_requirements:script=MUA_ColorConverter_CTKI%
pyinstaller %arguments:script=MUA_ColorConverter_CTKI% --noconfirm --windowed --add-data "%l:\=/%/customtkinter;customtkinter/"

REM set arguments=%arguments:onefile=onedir%
REM pyinstaller %arguments:script=MUA_ColorConverter_CTKI% --noconfirm --windowed --add-data "%l:\=/%/customtkinter;customtkinter/"
