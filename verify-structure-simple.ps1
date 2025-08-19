# Verify Third-Party Library Structure
# This script tests that the reorganized vendor structure works correctly

Write-Host "Verifying third-party library structure..." -ForegroundColor Cyan

# Check if all required directories exist
$requiredDirs = @(
    "static\vendor\jquery",
    "static\vendor\datatables", 
    "static\vendor\jsoneditor",
    "static\lib"
)

$missingDirs = @()
foreach ($dir in $requiredDirs) {
    if (-not (Test-Path $dir)) {
        $missingDirs += $dir
    }
}

if ($missingDirs.Count -gt 0) {
    Write-Host "ERROR: Missing directories:" -ForegroundColor Red
    $missingDirs | ForEach-Object { Write-Host "   - $_" -ForegroundColor Red }
    exit 1
}

# Check if all required files exist
$requiredFiles = @(
    "static\vendor\jquery\jquery-3.7.1.min.js",
    "static\vendor\datatables\jquery.dataTables.min.css",
    "static\vendor\datatables\jquery.dataTables.min.js",
    "static\vendor\jsoneditor\jsoneditor.min.css",
    "static\vendor\jsoneditor\jsoneditor.min.js",
    "static\lib\simple-json-diff.css",
    "static\lib\simple-json-diff.js"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "ERROR: Missing files:" -ForegroundColor Red
    $missingFiles | ForEach-Object { Write-Host "   - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "To download missing third-party libraries, run:" -ForegroundColor Yellow
    Write-Host "   See instructions in static\lib\README.md" -ForegroundColor Yellow
    exit 1
}

# Verify HTML references
Write-Host "SUCCESS: All directories present" -ForegroundColor Green
Write-Host "SUCCESS: All required files present" -ForegroundColor Green

# Check tools.html for correct references
$toolsHtml = Get-Content "static\tools.html" -Raw
$expectedPaths = @(
    "vendor/jquery/jquery-3.7.1.min.js",
    "vendor/datatables/jquery.dataTables.min.css",
    "vendor/datatables/jquery.dataTables.min.js", 
    "vendor/jsoneditor/jsoneditor.min.css",
    "vendor/jsoneditor/jsoneditor.min.js",
    "lib/simple-json-diff.css",
    "lib/simple-json-diff.js"
)

$invalidRefs = @()
foreach ($path in $expectedPaths) {
    if ($toolsHtml -notmatch [regex]::Escape($path)) {
        $invalidRefs += $path
    }
}

if ($invalidRefs.Count -gt 0) {
    Write-Host "ERROR: Invalid references in tools.html:" -ForegroundColor Red
    $invalidRefs | ForEach-Object { Write-Host "   - $_" -ForegroundColor Red }
    exit 1
}

Write-Host "SUCCESS: All HTML references correct" -ForegroundColor Green

Write-Host ""
Write-Host "VERIFICATION COMPLETE: Third-party library structure is correctly organized." -ForegroundColor Green
Write-Host ""
Write-Host "Current structure:" -ForegroundColor Cyan
Write-Host "   static/" -ForegroundColor White
Write-Host "   +-- lib/                    # Custom implementations" -ForegroundColor White
Write-Host "   |   +-- simple-json-diff.*  # Custom JSON diff" -ForegroundColor White
Write-Host "   |   +-- README.md          # Documentation" -ForegroundColor White
Write-Host "   +-- vendor/                # Third-party libraries" -ForegroundColor White
Write-Host "       +-- jquery/            # jQuery" -ForegroundColor White
Write-Host "       +-- datatables/        # DataTables" -ForegroundColor White
Write-Host "       +-- jsoneditor/        # JSON Editor" -ForegroundColor White
