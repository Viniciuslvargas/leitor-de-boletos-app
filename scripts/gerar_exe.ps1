$ErrorActionPreference = "Stop"
$raiz = Split-Path $PSScriptRoot -Parent
Set-Location $raiz
$versao = "1.0.0"

.\.venv\Scripts\python -m PyInstaller `
    --noconfirm --clean --windowed `
    --name LeitorDeBoletos `
    --icon "$raiz\src\leitor_boletos\dados\icone.ico" `
    --version-file "$raiz\scripts\versao_exe.txt" `
    --paths "$raiz\src" `
    --collect-data customtkinter `
    --add-data "$raiz\src\leitor_boletos\dados;leitor_boletos\dados" `
    --workpath "$raiz\build" --specpath "$raiz\build" --distpath "$raiz\dist" `
    "$raiz\iniciar.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou" }

$zip = "$raiz\dist\LeitorDeBoletos-$versao.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path "$raiz\dist\LeitorDeBoletos" -DestinationPath $zip

$hash = (Get-FileHash $zip -Algorithm SHA256).Hash
"$hash  LeitorDeBoletos-$versao.zip" | Out-File -Encoding ascii "$zip.sha256"
$tamanho = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Output "Pronto: $zip ($tamanho MB)"
Write-Output "SHA-256: $hash"
