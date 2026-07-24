# Inkscape AI - extension installer (Windows)
# Copies the extension into Inkscape's user extensions folder, verifies the
# copy, checks whether Inkscape is running, pings the live service, and shows
# a clean native dialog with the result.

$ErrorActionPreference = 'Stop'

$src  = Split-Path -Parent $MyInvocation.MyCommand.Path
$dest = Join-Path $env:APPDATA 'inkscape\extensions'
$files = @('send_to_ai.py', 'send_to_ai.inx')
$healthUrl = 'https://stitchbase.duckdns.org/health'

function Show-Result {
    param([bool]$Success, [string]$Heading, [string]$Body)

    # Preferred: a clean, modern WPF card.
    try {
        Add-Type -AssemblyName PresentationFramework | Out-Null

        $accentHex = if ($Success) { '#2E7D32' } else { '#C62828' }
        $headHex   = if ($Success) { '#1B5E20' } else { '#B71C1C' }

        [xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Inkscape AI" Width="480" SizeToContent="Height"
        WindowStartupLocation="CenterScreen" ResizeMode="NoResize"
        Background="#FFFFFF" FontFamily="Segoe UI" ShowInTaskbar="True" Topmost="True">
  <Grid>
    <Grid.RowDefinitions>
      <RowDefinition Height="6"/>
      <RowDefinition Height="*"/>
      <RowDefinition Height="Auto"/>
    </Grid.RowDefinitions>
    <Border x:Name="Accent" Grid.Row="0"/>
    <StackPanel Grid.Row="1" Margin="26,22,26,10">
      <TextBlock x:Name="Heading" FontSize="17" FontWeight="SemiBold" Margin="0,0,0,12"/>
      <TextBlock x:Name="Body" FontSize="12.5" Foreground="#333333" TextWrapping="Wrap" LineHeight="21"/>
    </StackPanel>
    <Border Grid.Row="2" Background="#F4F4F4" Padding="18,14">
      <Button x:Name="OkButton" Content="OK" Width="96" Height="32" HorizontalAlignment="Right"
              Foreground="White" BorderThickness="0" FontSize="12.5" FontWeight="SemiBold"/>
    </Border>
  </Grid>
</Window>
"@
        $reader = New-Object System.Xml.XmlNodeReader $xaml
        $win = [Windows.Markup.XamlReader]::Load($reader)

        $conv = New-Object System.Windows.Media.BrushConverter
        $accentBrush = $conv.ConvertFromString($accentHex)
        $headBrush   = $conv.ConvertFromString($headHex)

        $win.FindName('Accent').Background   = $accentBrush
        $win.FindName('Heading').Foreground  = $headBrush
        $win.FindName('Heading').Text        = $Heading
        $win.FindName('Body').Text           = $Body
        $ok = $win.FindName('OkButton')
        $ok.Background = $accentBrush
        $ok.Add_Click({ $win.Close() }) | Out-Null

        $win.ShowDialog() | Out-Null
        return
    } catch { }

    # Fallback 1: classic message box.
    try {
        Add-Type -AssemblyName System.Windows.Forms | Out-Null
        $icon = if ($Success) {
            [System.Windows.Forms.MessageBoxIcon]::Information
        } else {
            [System.Windows.Forms.MessageBoxIcon]::Error
        }
        [System.Windows.Forms.MessageBox]::Show(
            "$Heading`r`n`r`n$Body", 'Inkscape AI',
            [System.Windows.Forms.MessageBoxButtons]::OK, $icon) | Out-Null
        return
    } catch { }

    # Fallback 2: console.
    Write-Host ''
    Write-Host $Heading
    Write-Host $Body
    Write-Host ''
    Read-Host 'Press Enter to close'
}

Write-Host 'Installing Inkscape AI extension...'

# Copy + verify
$copied = $true
try {
    if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Force -Path $dest | Out-Null }
    foreach ($f in $files) {
        Copy-Item -Path (Join-Path $src $f) -Destination $dest -Force
    }
    foreach ($f in $files) {
        if (-not (Test-Path (Join-Path $dest $f))) { $copied = $false }
    }
} catch {
    $copied = $false
}

if (-not $copied) {
    $body = @"
Could not copy the extension files to:
$dest

Please copy send_to_ai.py and send_to_ai.inx into your Inkscape
user extensions folder manually (see INSTALL.txt), then restart Inkscape.
"@
    Write-Host $body
    Show-Result -Success $false -Heading 'Installation failed' -Body $body
    exit 1
}

# Is Inkscape currently running? (needs a full restart to load the extension)
$running = $false
try {
    if (Get-Process -Name 'inkscape' -ErrorAction SilentlyContinue) { $running = $true }
} catch { }

# Informational service reachability check (never fails the install)
$serviceLine = ''
try {
    $resp = Invoke-WebRequest -UseBasicParsing -TimeoutSec 6 -Uri $healthUrl
    if ($resp.StatusCode -eq 200) {
        $serviceLine = 'Service check: online and reachable.'
    } else {
        $serviceLine = "Service check: unexpected response ($($resp.StatusCode)). The install is fine; try again later."
    }
} catch {
    $serviceLine = 'Service check: could not reach the server right now (this does not affect the install).'
}

$restartLine = if ($running) {
    'Inkscape is open - fully close and reopen it now so the extension loads.'
} else {
    'Next: open Inkscape.'
}

$body = @"
Installed to:
$dest

$restartLine

Then use:
   Extensions  >  Inkscape AI  >  Send to AI Assistant

$serviceLine
"@

Write-Host $body
Show-Result -Success $true -Heading 'Installation successful' -Body $body
exit 0
