$ErrorActionPreference = "Stop"

$Namespace = "comptoir.coteaux"
$FlowId = "pipeline_comptoir"

Write-Host ""
Write-Host "========================================"
Write-Host " Comptoir des Coteaux - Pipeline Kestra"
Write-Host "========================================"
Write-Host ""

# ------------------------------------------------------------
# 1. Vérifications minimales
# ------------------------------------------------------------

if (-not (Test-Path ".\docker-compose.yaml")) {
    Write-Host "ERREUR : docker-compose.yaml introuvable." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".\flows\pipeline_comptoir.yaml")) {
    Write-Host "ERREUR : flows\pipeline_comptoir.yaml introuvable." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".\data")) {
    Write-Host "ERREUR : le dossier data\ est introuvable." -ForegroundColor Red
    exit 1
}

$sourceFiles = Get-ChildItem ".\data" -File |
    Where-Object {
        $_.Extension -in @(".csv", ".xlsx")
    }

if ($sourceFiles.Count -ne 3) {
    Write-Host ""
    Write-Host "ERREUR : data\ doit contenir exactement 3 fichiers CSV/XLSX." -ForegroundColor Red
    Write-Host "Fichiers actuellement détectés : $($sourceFiles.Count)" -ForegroundColor Red
    Write-Host ""

    if ($sourceFiles.Count -gt 0) {
        $sourceFiles | ForEach-Object {
            Write-Host " - $($_.Name)"
        }
    }

    exit 1
}

Write-Host "Sources détectées :" -ForegroundColor Cyan

$sourceFiles | ForEach-Object {
    Write-Host " - $($_.Name)"
}

Write-Host ""

# ------------------------------------------------------------
# 2. Vérification Docker
# ------------------------------------------------------------

Write-Host "[1/5] Vérification de Docker..." -ForegroundColor Cyan

docker info *> $null

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR : Docker n'est pas disponible." -ForegroundColor Red
    Write-Host "Démarre Docker Desktop puis relance .\run.ps1."
    exit 1
}

Write-Host "Docker est disponible." -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------
# 3. Démarrage de PostgreSQL et Kestra
# ------------------------------------------------------------

Write-Host "[2/5] Démarrage de l'environnement Docker..." -ForegroundColor Cyan

docker compose up -d postgres kestra

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR pendant le démarrage de Docker Compose." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "PostgreSQL et Kestra sont démarrés." -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------
# 4. Redéploiement du flow et des Namespace Files
# ------------------------------------------------------------

Write-Host "[3/5] Déploiement du flow, des SQL et des scripts Python..." -ForegroundColor Cyan

docker compose up -d --force-recreate kestra-init

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR pendant le lancement de kestra-init." -ForegroundColor Red
    exit 1
}

$initContainer = (
    docker compose ps -q kestra-init
).Trim()

if ([string]::IsNullOrWhiteSpace($initContainer)) {
    Write-Host "ERREUR : conteneur kestra-init introuvable." -ForegroundColor Red
    exit 1
}

Write-Host "Attente de la fin de kestra-init..."

while ($true) {

    $status = (
        docker inspect `
            --format '{{.State.Status}}' `
            $initContainer
    ).Trim()

    if ($status -eq "exited") {
        break
    }

    if ($status -eq "dead") {
        Write-Host "ERREUR : kestra-init est dans l'état DEAD." -ForegroundColor Red
        docker compose logs kestra-init --tail 100
        exit 1
    }

    Start-Sleep -Seconds 1
}

$initExitCode = [int](
    (
        docker inspect `
            --format '{{.State.ExitCode}}' `
            $initContainer
    ).Trim()
)

if ($initExitCode -ne 0) {

    Write-Host ""
    Write-Host "ERREUR : le déploiement Kestra a échoué." -ForegroundColor Red
    Write-Host ""

    docker compose logs kestra-init --tail 150

    exit 1
}

Write-Host "Flow et Namespace Files déployés avec succès." -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------
# 5. Exécution du pipeline
# ------------------------------------------------------------

Write-Host "[4/5] Exécution du pipeline Kestra..." -ForegroundColor Cyan
Write-Host ""

$executionOutput = docker compose run `
    --rm `
    --entrypoint kestractl `
    kestra-init `
    executions run `
    $Namespace `
    $FlowId `
    --wait `
    --output json

$kestractlExitCode = $LASTEXITCODE

if ($kestractlExitCode -ne 0) {
    Write-Host ""
    Write-Host "ERREUR : impossible de lancer l'exécution Kestra." -ForegroundColor Red
    exit 1
}

$jsonText = $executionOutput -join "`n"

try {
    $execution = $jsonText | ConvertFrom-Json
}
catch {
    Write-Host ""
    Write-Host "ERREUR : impossible d'interpréter la réponse JSON de Kestra." -ForegroundColor Red
    Write-Host ""
    Write-Host $jsonText
    exit 1
}

$executionId = $execution.id
$executionState = $execution.state.current

Write-Host ""
Write-Host "Execution ID : $executionId"
Write-Host "Etat final   : $executionState"
Write-Host ""

if ($executionState -ne "SUCCESS") {

    Write-Host "Le pipeline Kestra a échoué." -ForegroundColor Red
    Write-Host ""
    Write-Host "Logs d'erreur :" -ForegroundColor Yellow
    Write-Host ""

    docker compose run `
        --rm `
        --entrypoint kestractl `
        kestra-init `
        logs list `
        $executionId `
        --min-level ERROR

    exit 1
}

# ------------------------------------------------------------
# 6. Vérification des livrables
# ------------------------------------------------------------

Write-Host "[5/5] Vérification des livrables..." -ForegroundColor Cyan

$expectedOutputs = @(
    ".\outputs\chiffre_affaires.xlsx",
    ".\outputs\vins_premium.csv",
    ".\outputs\vins_ordinaires.csv"
)

$missingOutputs = @()

foreach ($file in $expectedOutputs) {

    if (-not (Test-Path $file)) {
        $missingOutputs += $file
    }
}

if ($missingOutputs.Count -gt 0) {

    Write-Host ""
    Write-Host "ERREUR : certains livrables sont absents :" -ForegroundColor Red

    foreach ($file in $missingOutputs) {
        Write-Host " - $file" -ForegroundColor Red
    }

    exit 1
}

Write-Host ""
Write-Host "========================================"
Write-Host " PIPELINE TERMINE AVEC SUCCES" -ForegroundColor Green
Write-Host "========================================"
Write-Host ""
Write-Host "Execution Kestra : $executionId"
Write-Host ""
Write-Host "Livrables :"
Write-Host " - outputs\chiffre_affaires.xlsx"
Write-Host " - outputs\vins_premium.csv"
Write-Host " - outputs\vins_ordinaires.csv"
Write-Host ""