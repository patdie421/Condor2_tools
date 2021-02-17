virtualenv venv
.\venv\Scripts\activate.ps1
pip install pyserial
pip install watchdog

wget "https://condorutill.fr/CoTaCo/CoTaCoV33.zip" -outfile "cotaco.zip"
Expand-Archive .\cotaco.zip -DestinationPath .
del "cotaco.zip"

wget "https://dl.google.com/android/repository/platform-tools-latest-windows.zip" -outfile "adb.zip"
Expand-Archive .\adb.zip -DestinationPath .
mkdir bin
copy .\platform-tools\adb.exe bin
copy .\platform-tools\AdbWinApi.dll bin
copy .\platform-tools\AdbWinUsbApi.dll bin
Remove-Item '.\platform-tools' -Recurse
del "adb.zip"
