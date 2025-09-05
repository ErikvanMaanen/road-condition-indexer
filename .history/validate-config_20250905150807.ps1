[CmdletBinding()]
# =============================================================================
# ROAD CONDITION INDEXER - ENVIRONMENT CONFIGURATION VALIDATOR
# =============================================================================
# This script validates that all required environment variables are properly
# configured across all deployment environments:
# - Local development (.env file)
# - Azure Web App (App Settings)
# - GitHub Codespaces (Repository Secrets/Variables)
# =============================================================================

param(
    [switch]$SkipAzure,
    [switch]$SkipGitHub,
    [switch]$Verbose
)

# Colors for output
$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"
$ColorInfo = "Cyan"

function Write-Status {
    param($Message, $Status = "Info")
    $color = switch ($Status) {
        "Success" { $ColorSuccess }
        "Warning" { $ColorWarning }
        "Error" { $ColorError }
        default { $ColorInfo }
    }
    Write-Host $Message -ForegroundColor $color
}

function Read-EnvFile {
    param($FilePath)
    $envVars = @{}
    if (-not (Test-Path $FilePath)) {
        Write-Status "❌ .env file not found at $FilePath" "Error"
        return $envVars
    }
    Write-Status "📄 Reading .env file (legacy flat parse for fallback)..." "Info"
    Get-Content $FilePath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
            $parts = $line.Split('=',2)
            if ($parts.Length -eq 2) { $envVars[$parts[0].Trim()] = $parts[1].Trim() }
        }
    }
    return $envVars
}

# Structured configuration parser aligned with new .env format
function Parse-EnvConfiguration {
    param([string]$FilePath = '.\\.env')
    $model = [ordered]@{
        Sections = @();                # Ordered list of section objects
        Variables = @{};               # name -> { value, secret:bool, sections:[..] }
        Requirements = [ordered]@{     # name -> { visibility: secret|public, sections:[..] }
        };
        Meta = [ordered]@{             # sectionName -> metaHashtable
        };
    }
    if (-not (Test-Path $FilePath)) { return $model }
    $currentSection = $null
    $lineNumber = 0
    foreach ($raw in Get-Content $FilePath) {
        $lineNumber++
        $line = $raw.TrimEnd()
        if (-not $line) { continue }
        # Section header
        if ($line -match '^\[SECTION +(.+?)\]') {
            $currentSection = $Matches[1].Trim()
            if (-not $model.Meta.ContainsKey($currentSection)) { $model.Meta[$currentSection] = @{} }
            $model.Sections += $currentSection
            continue
        }
        # Normalize comment lines beginning with '#'
        $core = $line
        if ($core.StartsWith('#')) { $core = $core.TrimStart('#').Trim() }
        if (-not $core) { continue }
        # Skip if not in a section for structured directives
        if (-not $currentSection) { continue }
        switch -regex ($core) {
            '^META +([^=]+)=(.+)$' {
                $k = $Matches[1].Trim(); $v = $Matches[2].Trim()
                $model.Meta[$currentSection][$k] = $v
            }
            '^(VAR|SECRET) +([A-Za-z0-9_]+)=(.+)$' {
                $type = $Matches[1]; $name = $Matches[2]; $val = $Matches[3].Trim()
                if (-not $model.Variables.ContainsKey($name)) {
                    $model.Variables[$name] = [ordered]@{ value = $val; secret = ($type -eq 'SECRET'); sections = @($currentSection) }
                } else {
                    # Preserve first value; append section and possibly upgrade to secret
                    $existing = $model.Variables[$name]
                    if (-not $existing.sections.Contains($currentSection)) { $existing.sections += $currentSection }
                    if ($type -eq 'SECRET') { $existing.secret = $true }
                }
            }
            '^REQUIRE +([A-Za-z0-9_]+) +(secret|public)$' {
                $rName = $Matches[1]; $vis = $Matches[2]
                if (-not $model.Requirements.ContainsKey($rName)) {
                    $model.Requirements[$rName] = [ordered]@{ visibility = $vis; sections = @($currentSection) }
                } else {
                    $req = $model.Requirements[$rName]
                    if (-not $req.sections.Contains($currentSection)) { $req.sections += $currentSection }
                    # If any section marks as secret escalate to secret
                    if ($vis -eq 'secret') { $req.visibility = 'secret' }
                }
            }
            '^NOTE ' { }
            default { }
        }
    }
    return $model
}

# Parse Azure Web App config (App Name & Resource Group) from commented section in .env
function Parse-AzureSectionFromEnvFile {
    param(
        [string]$FilePath = '.\\.env'
    )
    $result = @{}
    if (-not (Test-Path $FilePath)) { return $result }
    try {
        $lines = Get-Content $FilePath
        $inSection = $false
        foreach ($raw in $lines) { # $raw = $lines[23]
            $line = $raw.Trim()
            Write-Verbose $line
            if ($line -match '^# +AZURE WEB APP CONFIGURATION') { $inSection = $true; continue }
            if ($inSection) {
                # Stop if we reach a blank line followed by non comment or next major separator
                if ($line -match '^# ==+' ) { return }
                # If the line contains a ' : ' pattern, extract key/value
                # Example: # - Subscription Name: raet experimental
                # Example result should be: @{ SubscriptionName = "raet experimental" }
                if ($line -match '^# *- *(.+?):\s*(.+)$') {
                    $key = $Matches[1].Trim()
                    $value = $Matches[2].Trim()
                    $result[$key] = $value
                }
            }
        }
    } catch { }
    return $result
}

function Get-RequiredVariables {
    param($EnvVars)
    
    $requiredVars = @($EnvVars.Keys | Sort-Object)
    $secretVars = @()
    $publicVars = @()
    
    # Categorize variables based on naming patterns
    foreach ($var in $requiredVars) {
        if ($var.ToUpper().Contains("PASSWORD") -or 
            $var.ToUpper().Contains("SECRET") -or 
            $var.ToUpper().Contains("KEY") -or
            $var.ToUpper().Contains("TOKEN")) {
            $secretVars += $var
        } else {
            $publicVars += $var
        }
    }
    
    Write-Status "🔍 Detected $($requiredVars.Count) total variables:" "Info"
    Write-Status "  - $($secretVars.Count) secrets (password/key/token/secret)" "Info" 
    Write-Status "  - $($publicVars.Count) public variables" "Info"
    
    return $requiredVars, $secretVars, $publicVars
}

function Ensure-AzModule {
    if (-not (Get-Module -ListAvailable -Name Az.Accounts)) {
        Write-Status "📦 Installing Az PowerShell modules (Az.Accounts)..." "Info"
        try {
            Install-Module Az -Scope CurrentUser -Force -ErrorAction Stop | Out-Null
        }
        catch {
            Write-Status "❌ Failed to install Az module: $($_.Exception.Message)" "Error"
            return $false
        }
    }
    return $true
}

function Test-AzLogin {
    try {
        $ctx = Get-AzContext 2>$null
        if (-not $ctx) { return $false }
        return $true
    } catch { return $false }
}

function Ensure-AzLogin {
    if (-not (Ensure-AzModule)) { return $false }
    if (Test-AzLogin) { return $true }
    Write-Status "🔐 Not logged into Azure, attempting interactive login..." "Info"
    try {
        Connect-AzAccount -ErrorAction Stop | Out-Null
        return (Test-AzLogin)
    } catch {
        Write-Status "❌ Azure login failed: $($_.Exception.Message)" "Error"
        return $false
    }
}

function Test-GitHubCLI {
    try {
        $null = gh auth status 2>$null
        return $true
    } catch {
        return $false
    }
}

function Get-AzureWebAppSettings {
    param(
        [Parameter(Mandatory)][string]$AppName,
        [Parameter(Mandatory)][string]$ResourceGroupName
    )

    if (-not (Ensure-AzLogin)) {
        Write-Status "❌ Azure context unavailable (Az login failed)" "Error"
        return @{}
    }

    Write-Status "🔍 Checking Azure Web App settings via Az module..." "Info"
    try {
        $AzWebApp = Get-AzWebApp -Name $AppName -ResourceGroupName $ResourceGroupName -ErrorAction Stop
        $AzWebAppSettings = $AzWebApp.SiteConfig.AppSettings
        Write-Status "✅ Retrieved $($AzWebAppSettings.Count) app settings from Azure" "Success"
        return $AzWebAppSettings
    } catch {
        Write-Status "❌ Failed to retrieve Azure Web App settings: $($_.Exception.Message)" "Error"
        return @{}
    }
}

function Get-GitHubSecrets {
    param($Owner, $Repo)
    
    if (-not (Test-GitHubCLI)) {
        Write-Status "❌ GitHub CLI not available or not authenticated" "Error"
        return @{}, @{}
    }
    
    Write-Status "🔍 Checking GitHub repository secrets and variables..." "Info"
    
    try {
        # Get Codespaces secrets
        $secretsJson = gh api "repos/$Owner/$Repo/codespaces/secrets" -jq '.secrets[].name' 2>$null
        $secrets = @{}
        if ($secretsJson) {
            $secretsJson | ForEach-Object { $secrets[$_] = "***SET***" }
        }
        
        # Get Codespaces variables  
        $variablesJson = gh api "repos/$Owner/$Repo/codespaces/variables" -jq '.variables[] | {name: .name, value: .value}' 2>$null
        $variables = @{}
        if ($variablesJson) {
            ($variablesJson | ConvertFrom-Json) | ForEach-Object { 
                $variables[$_.name] = $_.value 
            }
        }
        
        Write-Status "✅ Found $($secrets.Count) secrets and $($variables.Count) variables in GitHub" "Success"
        return $secrets, $variables
    } 
    catch {
        Write-Status "❌ Failed to retrieve GitHub settings: $($_.Exception.Message)" "Error"
        return @{}, @{}
    }
}

function Test-VariableExists {
    param($VarName, $Source, $SourceName, $IsSecret = $false)
    
    if ($Source.ContainsKey($VarName)) {
        $value = $Source[$VarName]
        if ($IsSecret -or $VarName.ToUpper().Contains("PASSWORD")) {
            Write-Status "  ✅ $VarName = ***SET***" "Success"
        } else {
            Write-Status "  ✅ $VarName = $value" "Success"
        }
        return $true
    } else {
        Write-Status "  ❌ $VarName = MISSING" "Error"
        return $false
    }
}

# Main script execution
Write-Status "🚀 Road Condition Indexer - Configuration Validator" "Info"
Write-Status "=" * 60 "Info"

# Read .env file
$envVars = Read-EnvFile ".\.env"

# Structured parse (preferred). Fallback to legacy variable listing.
$configModel = Parse-EnvConfiguration -FilePath '.\\.env'
$isStructured = ($configModel.Sections.Count -gt 0 -and $configModel.Meta.Keys -contains 'AzureWebApp')
if ($isStructured) {
    Write-Status "🧩 Detected structured configuration format (.env sections)." "Success"
} else {
    Write-Status "ℹ️  Structured sections not detected – using legacy flat parsing." "Warning"
}

# Compute required variables & classification from model when structured
if ($isStructured) {
    $requiredVars = @($configModel.Requirements.Keys | Sort-Object)
    $secretVars = @($configModel.Requirements.GetEnumerator() | Where-Object { $_.Value.visibility -eq 'secret' } | ForEach-Object { $_.Key } | Sort-Object)
    $publicVars = @($configModel.Requirements.GetEnumerator() | Where-Object { $_.Value.visibility -eq 'public' } | ForEach-Object { $_.Key } | Sort-Object)
} else {
    # Legacy path: derive from flat env vars
    $envVars = Read-EnvFile '.\\.env'
    if ($envVars.Count -eq 0) { Write-Status '❌ No variables found in .env file. Cannot proceed with validation.' 'Error'; exit 1 }
    $requiredVars, $secretVars, $publicVars = Get-RequiredVariables $envVars
}

# Materialize a lookup of local values (structured or legacy)
$localValues = @{}
if ($isStructured) {
    foreach ($kv in $configModel.Variables.GetEnumerator()) { $localValues[$kv.Key] = $kv.Value.value }
} else {
    $localValues = $envVars
}

# Azure identifiers
$azureAppName = if ($isStructured -and $configModel.Meta['AzureWebApp'].AppName) { $configModel.Meta['AzureWebApp'].AppName } else { 'rci-nl' }
$azureRg       = if ($isStructured -and $configModel.Meta['AzureWebApp'].ResourceGroup) { $configModel.Meta['AzureWebApp'].ResourceGroup } else { 'ErikMaa' }
Write-Status "🔧 Azure Target: AppName='$azureAppName' ResourceGroup='$azureRg'" 'Info'

if ($requiredVars.Count -eq 0) { Write-Status '❌ No required variables determined from configuration model.' 'Error'; exit 1 }

if ($envVars.Count -eq 0) {
    Write-Status "❌ No variables found in .env file. Cannot proceed with validation." "Error"
    exit 1
}

# Dynamically determine required variables from .env file
$requiredVars, $secretVars, $publicVars = Get-RequiredVariables $envVars

# Validation results
$results = @{
    Local  = @{ Success = 0; Missing = 0; Total = $requiredVars.Count }
    Azure  = @{ Success = 0; Missing = 0; Total = $requiredVars.Count }
    GitHub = @{ Success = 0; Missing = 0; Total = $requiredVars.Count }
}

# Validate local values (structured or legacy)
Write-Status "`n📄 VALIDATING LOCAL CONFIGURATION" 'Info'
Write-Status ('-' * 40) 'Info'
foreach ($var in $requiredVars) {
    if (Test-VariableExists $var $localValues 'Local') { $results.Local.Success++ } else { $results.Local.Missing++ }
}

# Validate Azure Web App settings
if (-not $SkipAzure) {
    Write-Status "`n☁️  VALIDATING AZURE WEB APP SETTINGS" "Info"
    Write-Status "-" * 40 "Info"
    
    $azureSettings = Get-AzureWebAppSettings -AppName $azureAppName -ResourceGroup $azureRg
    
    if ($azureSettings.Count -gt 0) {
        foreach ($var in $requiredVars) {
            if (Test-VariableExists $var $azureSettings "Azure") {
                $results.Azure.Success++
            } else {
                $results.Azure.Missing++
            }
        }
    } else {
        Write-Status "⚠️  Skipping Azure validation due to connection issues" "Warning"
        $results.Azure.Missing = $requiredVars.Count
    }
} else {
    Write-Status "`n☁️  SKIPPING AZURE VALIDATION (-SkipAzure specified)" "Warning"
}

# Validate GitHub repository settings
if (-not $SkipGitHub) {
    Write-Status "`n🐙 VALIDATING GITHUB REPOSITORY SETTINGS" "Info"  
    Write-Status "-" * 40 "Info"
    
    $githubSecrets, $githubVariables = Get-GitHubSecrets 'ErikvanMaanen' 'road-condition-indexer'
    
    if (($githubSecrets.Count + $githubVariables.Count) -gt 0) {
        # Check secrets
        foreach ($var in $secretVars) {
            if (Test-VariableExists $var $githubSecrets "GitHub Secrets" $true) {
                $results.GitHub.Success++
            } else {
                $results.GitHub.Missing++
            }
        }
        
        # Check variables
        foreach ($var in $publicVars) {
            if (Test-VariableExists $var $githubVariables "GitHub Variables") {
                $results.GitHub.Success++
            } else {
                $results.GitHub.Missing++
            }
        }
    } else {
        Write-Status "⚠️  Skipping GitHub validation due to connection issues" "Warning"
        $results.GitHub.Missing = $requiredVars.Count
    }
} else {
    Write-Status "`n🐙 SKIPPING GITHUB VALIDATION (-SkipGitHub specified)" "Warning"
}

# Summary report
Write-Status "`n📊 VALIDATION SUMMARY" "Info"
Write-Status "=" * 60 "Info"

$environments = @("Local", "Azure", "GitHub")
$allPassed = $true

foreach ($env in $environments) {
    $result = $results[$env]
    $status = if ($result.Missing -eq 0) { "Success" } else { "Error" }
    $icon = if ($result.Missing -eq 0) { "✅" } else { "❌" }
    
    Write-Status "$icon $env Environment: $($result.Success)/$($result.Total) variables configured" $status
    
    if ($result.Missing -gt 0) {
        $allPassed = $false
    }
}

Write-Status "`n" + "=" * 60 "Info"

if ($allPassed) {
    Write-Status "🎉 ALL ENVIRONMENTS CONFIGURED CORRECTLY!" "Success"
    Write-Status "The application should work properly in all deployment scenarios." "Success"
    exit 0
} else {
    Write-Status "⚠️  CONFIGURATION ISSUES DETECTED!" "Warning"
    Write-Status "Please review the missing variables above and configure them in the respective environments." "Warning"
    Write-Status "`nFor setup instructions, refer to the .env file comments." "Info"
    exit 1
}
