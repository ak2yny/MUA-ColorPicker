for /f "tokens=1* delims=: " %%k in ('pip show customtkinter ^| findstr /bl "Location"') do set l=%%l
if not errorlevel 0 exit

set arguments=--specpath dist --onefile --version-file=..\script.txt --icon=..\MM.ico script.pyw  --add-data "..\MM.ico;."
pyinstaller %arguments:script=MUA_ColorConverter_CTKI% --noconfirm --windowed --add-data "%l:\=/%/customtkinter;customtkinter/"
pyinstaller %arguments:script=MUA_ColorConverter% --add-data "..\tkBreeze;tkBreeze"

a%arguments:onefile=onedir%
pyinstaller %arguments:script=MUA_ColorConverter_CTKI% --noconfirm --windowed --add-data "%l:\=/%/customtkinter;customtkinter/"
