# JTECH PATH Setup
# Run this to add jtech to your PATH permanently

$scriptsPath = "C:\Users\user\AppData\Roaming\Python\Python314\Scripts"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($userPath -like "*$scriptsPath*") {
    Write-Host "JTECH is already in your PATH. You're good to go!"
} else {
    $newPath = $userPath + ";" + $scriptsPath
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "JTECH added to PATH! Restart your terminal to use 'jtech' from anywhere."
}

Write-Host ""
Write-Host "Try it:  jtech --help"
Write-Host "Or:      jtech web"
