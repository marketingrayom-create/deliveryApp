$ErrorActionPreference = 'Stop'
$updatedExe = Join-Path $PSScriptRoot 'AmazonDeliveryApp_Groq_Optimized.exe'
Start-Process -FilePath $updatedExe -ArgumentList '--port','5070' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
