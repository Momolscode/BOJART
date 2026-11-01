# Audit en lecture seule. Aucun réseau, aucune installation, aucun changement système.
# Lancement natif Windows : Python n'est pas nécessaire.
$ErrorActionPreference = 'Stop'
$r = [ordered]@{ schema='bojart.hardware.windows.v2'; observedAtUtc=[DateTime]::UtcNow.ToString('o'); scope='this_computer_only'; installed=$false; networkCalls=0; physicalCommandsSent=0 }
try { $o=Get-CimInstance Win32_OperatingSystem; $r.os=@{name=$o.Caption;version=$o.Version;architecture=$o.OSArchitecture} } catch { $r.os=@{status='unavailable'} }
try { $r.cpu=@(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors) } catch { $r.cpu=@{status='unavailable'} }
try { $c=Get-CimInstance Win32_ComputerSystem; $r.ramGiB=[math]::Round($c.TotalPhysicalMemory/1GB,2) } catch { $r.ramGiB=$null }
try { $r.gpu=@(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion);$r.gpuNote='VRAM non déduite de Win32_VideoController.AdapterRAM : valeur non fiable pour certains GPU.' } catch { $r.gpu=@() }
try {
 $n=Get-Command nvidia-smi -ErrorAction Stop
 $p=New-Object System.Diagnostics.Process; $p.StartInfo.FileName=$n.Source
 $p.StartInfo.Arguments='--query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits'
 $p.StartInfo.UseShellExecute=$false;$p.StartInfo.RedirectStandardOutput=$true;$p.StartInfo.RedirectStandardError=$true;$p.StartInfo.CreateNoWindow=$true
 [void]$p.Start()
 if($p.WaitForExit(6000)) { $r.nvidiaSmi=$p.StandardOutput.ReadToEnd();$r.nvidiaExitCode=$p.ExitCode } else { $p.Kill();$r.nvidiaSmi='timeout' }
 $p.Dispose()
} catch { $r.nvidiaSmi='unavailable' }
try { $r.disks=@(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID,@{N='totalGiB';E={[math]::Round($_.Size/1GB,2)}},@{N='freeGiB';E={[math]::Round($_.FreeSpace/1GB,2)}}) } catch { $r.disks=@() }
try { Add-Type -AssemblyName System.Windows.Forms; $r.screens=@([System.Windows.Forms.Screen]::AllScreens | ForEach-Object { @{width=$_.Bounds.Width;height=$_.Bounds.Height;primary=$_.Primary} });$r.screenScope='session graphique courante' } catch { $r.screens=@() }
try { $r.audio=@(Get-CimInstance Win32_SoundDevice | Select-Object Name,Status) } catch { $r.audio=@() }
$r.qualification=@{ printersVerified=$false;modelsBenchmarked=$false;microphoneTested=$false;threeScreensTested=$false }
$r.notes='Aucun numéro de série, compte, clé, média ou fichier personnel recherché. Puissance alimentation/refroidissement à vérifier physiquement. Script Windows écrit mais non exécuté sur le PC cible.'
$out=Join-Path $PSScriptRoot 'rapports';[void](New-Item -ItemType Directory -Path $out -Force)
$file=Join-Path $out ('BOJART_PC_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')+'.json')
$r | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $file -Encoding UTF8
Write-Host ('Rapport créé : '+$file)
