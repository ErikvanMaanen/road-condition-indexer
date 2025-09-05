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
    
    Write-Status "📄 Reading .env file..." "Info"
    
    Get-Content $FilePath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()
                $envVars[$key] = $value
                if ($Verbose) {
                    if ($key.ToUpper().Contains("PASSWORD") -or $key.ToUpper().Contains("SECRET")) {
                        Write-Status "  $key=***HIDDEN***" "Info"
                    } else {
                        Write-Status "  $key=$value" "Info"
                    }
                }
            }
        }
    }
    
    Write-Status "✅ Found $($envVars.Count) variables in .env file" "Success"
    return $envVars
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

function Test-AzureCLI {
    try {
        $null = az account show 2>$null
        return $true
    } catch {
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
    param($AppName, $ResourceGroup)
    
    if (-not (Test-AzureCLI)) {
        Write-Status "❌ Azure CLI not available or not logged in" "Error"
        return @{}
    }
    
    Write-Status "🔍 Checking Azure Web App settings..." "Info"
    
    try {
        $settings = az webapp config appsettings list --name $AppName --resource-group $ResourceGroup --query "[].{name:name,value:value}" | ConvertFrom-Json
        $settingsHash = @{}
        
        foreach ($setting in $settings) {
            $settingsHash[$setting.name] = $setting.value
        }
        
        Write-Status "✅ Retrieved $($settingsHash.Count) app settings from Azure" "Success"
        return $settingsHash
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
        $secretsJson = gh api "repos/$Owner/$Repo/codespaces/secrets" --jq '.secrets[].name' 2>$null
        $secrets = @{}
        if ($secretsJson) {
            $secretsJson | ForEach-Object { $secrets[$_] = "***SET***" }
        }
        
        # Get Codespaces variables  
        $variablesJson = gh api "repos/$Owner/$Repo/codespaces/variables" --jq '.variables[] | {name: .name, value: .value}' 2>$null
        $variables = @{}
        if ($variablesJson) {
            ($variablesJson | ConvertFrom-Json) | ForEach-Object { 
                $variables[$_.name] = $_.value 
            }
        }
        
        Write-Status "✅ Found $($secrets.Count) secrets and $($variables.Count) variables in GitHub" "Success"
        return $secrets, $variables
    } catch {
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

if ($envVars.Count -eq 0) {
    Write-Status "❌ No variables found in .env file. Cannot proceed with validation." "Error"
    exit 1
}

# Dynamically determine required variables from .env file
$requiredVars, $secretVars, $publicVars = Get-RequiredVariables $envVars

# Validation results
$results = @{
    Local = @{ Success = 0; Missing = 0; Total = $requiredVars.Count }
    Azure = @{ Success = 0; Missing = 0; Total = $requiredVars.Count }
    GitHub = @{ Success = 0; Missing = 0; Total = $requiredVars.Count }
}

# Validate local .env file (all variables should exist by definition)
Write-Status "`n📄 VALIDATING LOCAL .ENV FILE" "Info"
Write-Status "-" * 40 "Info"

foreach ($var in $requiredVars) {
    if (Test-VariableExists $var $envVars "Local") {
        $results.Local.Success++
    } else {
        $results.Local.Missing++
    }
}

# Validate Azure Web App settings
if (-not $SkipAzure) {
    Write-Status "`n☁️  VALIDATING AZURE WEB APP SETTINGS" "Info"
    Write-Status "-" * 40 "Info"
    
    $azureSettings = Get-AzureWebAppSettings "rci-nl" "ErikMaa"
    
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
    Write-Status "`n☁️  SKIPPING AZURE VALIDATION (--SkipAzure specified)" "Warning"
}

# Validate GitHub repository settings
if (-not $SkipGitHub) {
    Write-Status "`n🐙 VALIDATING GITHUB REPOSITORY SETTINGS" "Info"  
    Write-Status "-" * 40 "Info"
    
    $githubSecrets, $githubVariables = Get-GitHubSecrets "ErikvanMaanen" "road-condition-indexer"
    
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
    Write-Status "`n🐙 SKIPPING GITHUB VALIDATION (--SkipGitHub specified)" "Warning"
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