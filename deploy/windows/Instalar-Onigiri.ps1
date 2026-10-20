param(
    [ValidatePattern('^[a-zA-Z0-9.-]+$')]
    [string]$Raspberry = '100.95.225.112',
    [switch]$InstalarOdometria,
    [switch]$InstalarRuntime,
    [switch]$InstalarCamera,
    [switch]$InstalarRGBD
)
$ErrorActionPreference = 'Stop'
$packagePath = Join-Path $PSScriptRoot 'onigiri-painel-raspberry.tar.gz'
if (-not (Test-Path -LiteralPath $packagePath)) { throw 'Mantenha o pacote .tar.gz na mesma pasta deste instalador.' }
$releaseName = 'onigiri-panel-' + [guid]::NewGuid().ToString('N')
$destination = 'onigiri@' + $Raspberry
Write-Host 'Copiando atualização para o Raspberry. Digite a senha quando solicitada.'
& scp -o StrictHostKeyChecking=yes $packagePath "${destination}:/home/onigiri/$releaseName.tar.gz"
if ($LASTEXITCODE -ne 0) { throw 'A cópia falhou. Confira conexão, usuário e senha.' }
$installCommand = "mkdir /home/onigiri/$releaseName && tar -xzf /home/onigiri/$releaseName.tar.gz -C /home/onigiri/$releaseName && bash /home/onigiri/$releaseName/install.sh"
if ($InstalarOdometria) {
    $installCommand += ' && bash /home/onigiri/onigiri/deploy/scripts/install_lidar_odometry.sh'
    Write-Host 'Também será instalado e compilado o RF2O no Raspberry. Esta etapa pode levar alguns minutos.'
}
if ($InstalarRuntime) { $installCommand += ' && bash /home/onigiri/onigiri/deploy/scripts/install_robot_runtime.sh' }
if ($InstalarCamera) { $installCommand += ' && bash /home/onigiri/onigiri/deploy/scripts/install_orbbec.sh' }
if ($InstalarRGBD) { $installCommand += ' && bash /home/onigiri/onigiri/deploy/scripts/install_rgbd.sh' }
Write-Host 'Instalando. O sudo pode solicitar novamente a senha do usuário onigiri.'
& ssh -t -o StrictHostKeyChecking=yes $destination $installCommand
if ($LASTEXITCODE -ne 0) { throw 'A instalação não foi concluída. Preserve a mensagem de erro para diagnóstico.' }
Write-Host ''
Write-Host 'Abrindo acesso ao painel em http://localhost:8081/#maps'
Write-Host 'Mantenha esta janela aberta durante o uso. O painel WSL na porta 8080 permanece separado.'
$existingListener = Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue
if ($existingListener) {
    Write-Host 'A porta 8081 já está em uso. Se o túnel anterior está aberto, continue usando-o e atualize a página.'
    return
}
& ssh -N -o StrictHostKeyChecking=yes -o ExitOnForwardFailure=yes -L 8081:127.0.0.1:8080 $destination
if ($LASTEXITCODE -ne 0) { throw 'O túnel SSH foi encerrado ou não pôde ser aberto.' }
