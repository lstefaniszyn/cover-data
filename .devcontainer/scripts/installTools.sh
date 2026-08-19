#!/bin/bash

# =============================================================================
# Dev Container Tools Installation Script
# =============================================================================
# This script installs various development tools for the dev container
# including SQL Server tools, Azure CLI, OpenShift CLI, Helm, Terraform, etc.
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# =============================================================================
# Configuration
# =============================================================================
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="/tmp/install_tools.log"
readonly TEMP_DIR="/tmp/tools_install"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# =============================================================================
# Logging Functions
# =============================================================================
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} $message"
            ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# =============================================================================
# Utility Functions
# =============================================================================
check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

run_command() {
    local cmd="$*"
    log "DEBUG" "Running: $cmd"
    
    if eval "$cmd"; then
        log "DEBUG" "Command succeeded: $cmd"
        return 0
    else
        log "ERROR" "Command failed: $cmd"
        return 1
    fi
}

download_file() {
    local url="$1"
    local output="$2"
    
    log "DEBUG" "Downloading: $url -> $output"
    
    if wget --timeout=60 --tries=3 -O "$output" "$url"; then
        log "DEBUG" "Download successful: $url"
        return 0
    else
        log "ERROR" "Download failed: $url"
        return 1
    fi
}

# =============================================================================
# System Detection
# =============================================================================
detect_system() {
    log "INFO" "Detecting system information..."
    
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        DISTRO_ID=$(echo "$ID" | tr '[:upper:]' '[:lower:]')
        VERSION_ID=$(echo "$VERSION_ID")
        DISTRO_CODENAME=$(echo "$VERSION_CODENAME" | tr '[:upper:]' '[:lower:]')
        
        log "INFO" "Detected distribution: ${DISTRO_ID}, version: ${VERSION_ID}, codename: ${DISTRO_CODENAME}"
    else
        log "ERROR" "Could not detect OS distribution"
        exit 1
    fi
    
    # Detect architecture
    ARCH=$(dpkg --print-architecture)
    log "INFO" "Detected architecture: ${ARCH}"
    
    # Detect GLIBC version
    ldd_output=$(ldd --version)
    sed_result=$(echo "$ldd_output" | head -n1 | sed 's/.*GLIBC \([0-9]\+\.[0-9]\+\).*/\1/')
    GLIBC_VERSION="$sed_result"
    log "INFO" "Detected GLIBC version: ${GLIBC_VERSION}"
}

# =============================================================================
# Installation Functions
# =============================================================================
install_chrome() {
    log "INFO" "Installing Google Chrome..."
    
    # Skip Chrome installation on macOS
    if [[ "$(uname)" == "Darwin" ]]; then
        log "INFO" "Skipping Chrome installation on macOS"
        return 0
    fi
    
    # Only install Chrome on Linux AMD64
    if [[ "$ARCH" != "amd64" ]]; then
        log "INFO" "Chrome installation only supported for Linux AMD64"
        return 0
    fi
    
    log "INFO" "Installing Chrome for Linux AMD64"
    
    # Download and install Chrome
    local chrome_url="https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
    
    if ! download_file "$chrome_url" "/tmp/chrome.deb"; then
        log "ERROR" "Failed to download Chrome"
        return 1
    fi
    
    if ! run_command "sudo apt-get update"; then
        log "ERROR" "Failed to update package lists"
        return 1
    fi
    
    # Use apt-get to install .deb and resolve dependencies
    if ! run_command "sudo apt-get install -y /tmp/chrome.deb"; then
        log "WARN" "Chrome install via apt-get failed, attempting to fix broken dependencies"
        if ! run_command "sudo apt --fix-broken install -y"; then
            log "ERROR" "Failed to fix broken dependencies after Chrome install"
            return 1
        fi
        # Try installing Chrome again
        if ! run_command "sudo apt-get install -y /tmp/chrome.deb"; then
            log "ERROR" "Failed to install Chrome after fixing dependencies"
            return 1
        fi
    fi
    run_command "rm /tmp/chrome.deb"
    log "INFO" "Google Chrome installed successfully for Linux AMD64"
}

install_sql_server_tools() {
    log "INFO" "Installing SQL Server tools (sqlcmd, bcp)..."
    
    # Download Microsoft GPG key using wget (works better with corporate SSL inspection)
    log "INFO" "Downloading Microsoft GPG key..."
    if wget --timeout=60 --tries=3 -O- https://packages.microsoft.com/keys/microsoft.asc | sudo tee /etc/apt/trusted.gpg.d/microsoft.asc; then
        log "INFO" "Successfully downloaded Microsoft GPG key"
    else
        log "ERROR" "Failed to download Microsoft GPG key"
        return 1
    fi
    
    # Add repository configuration
    local repo_config="deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/microsoft.asc] https://packages.microsoft.com/${DISTRO_ID}/${VERSION_ID}/prod ${DISTRO_CODENAME} main"
    if ! run_command "echo '$repo_config' | sudo tee /etc/apt/sources.list.d/microsoft.list"; then
        log "ERROR" "Failed to add Microsoft repository"
        return 1
    fi
    
    # Update and install
    if ! run_command "sudo apt-get update"; then
        log "ERROR" "Failed to update package lists"
        return 1
    fi
    
    if ! run_command "sudo ACCEPT_EULA=Y apt-get install -y mssql-tools18 unixodbc-dev"; then
        log "ERROR" "Failed to install SQL Server tools"
        return 1
    fi
    
    # Create symlinks
    run_command "sudo ln -sf /opt/mssql-tools18/bin/sqlcmd /usr/local/bin/sqlcmd"
    run_command "sudo ln -sf /opt/mssql-tools18/bin/bcp /usr/local/bin/bcp"
    
    log "INFO" "SQL Server tools installed successfully"
}

install_azure_cli() {
    log "INFO" "Installing Azure CLI, kubectl, and kubelogin..."
    
    # Add Azure CLI repository (reusing existing Microsoft GPG key)
    log "INFO" "Adding Azure CLI repository..."
    
    # Add Azure CLI repository configuration (using existing Microsoft GPG key)
    local azure_repo="deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/microsoft.asc] https://packages.microsoft.com/repos/azure-cli/ $(lsb_release -cs) main"
        if run_command "echo '$azure_repo' | sudo tee /etc/apt/sources.list.d/azure-cli.list"; then
            log "INFO" "Successfully added Azure CLI repository"
            
            # Update and install Azure CLI
            if run_command "sudo apt-get update && sudo apt-get install -y azure-cli"; then
                log "INFO" "Azure CLI installed via Microsoft repository"
            else
                log "WARN" "Failed to install Azure CLI via repository, skipping installation"
                log "INFO" "Azure CLI will need to be installed manually if required"
                return 0
            fi
        else
            log "ERROR" "Failed to add Azure CLI repository"
            return 1
        fi
    
    if ! run_command "az aks install-cli"; then
        log "ERROR" "Failed to install kubectl"
        return 1
    fi
    
    log "INFO" "Azure CLI, kubectl, and kubelogin installed successfully"
}

install_git_credential_manager() {
    log "INFO" "Installing Git Credential Manager..."
    
    # Fallback version in case GitHub API is rate limited
    local fallback_version="2.7.0"
    
    # Try to get latest version from GitHub API
    local gcm_version
    gcm_version=$(wget --timeout=60 --tries=3 -O- https://api.github.com/repos/git-ecosystem/git-credential-manager/releases/latest 2>/dev/null | grep tag_name | cut -d '"' -f4 | sed 's/^v//')
    
    if [[ -z "$gcm_version" ]]; then
        log "WARN" "Failed to get latest GCM version from GitHub API (possibly rate limited)"
        log "INFO" "Using fallback version: $fallback_version"
        gcm_version="$fallback_version"
    else
        log "INFO" "Using latest GCM version: $gcm_version"
    fi
    
    # Download and install (only called on AMD64 systems)
    # Note: GCM 2.7.0+ uses new naming convention: gcm-linux-x64-{version}.deb
    # Older versions used: gcm-linux_amd64.{version}.deb
    local gcm_url="https://github.com/git-ecosystem/git-credential-manager/releases/download/v${gcm_version}/gcm-linux-x64-${gcm_version}.deb"
    
    # GCM download often fails through corporate proxies due to SSL tunneling issues
    # (GitHub releases redirect to release-assets.githubusercontent.com which requires CONNECT)
    # Treat this as non-critical - Git credentials can be managed via VS Code or manual setup
    if ! download_file "$gcm_url" "/tmp/gcm.deb"; then
        log "WARN" "Failed to download GCM (likely proxy SSL tunneling issue)"
        log "WARN" "Git Credential Manager will need to be installed manually if required"
        log "INFO" "Alternative: Use VS Code's built-in Git credential management"
        return 0  # Non-critical, don't fail the build
    fi
    
    if ! run_command "sudo dpkg -i /tmp/gcm.deb"; then
        log "WARN" "Failed to install GCM package"
        log "INFO" "Git Credential Manager will need to be installed manually if required"
        return 0  # Non-critical, don't fail the build
    fi
    
    run_command "rm /tmp/gcm.deb"
    log "INFO" "Git Credential Manager installed successfully"
}

install_openshift_cli() {
    log "INFO" "Installing OpenShift CLI (oc)..."
    
    # Select OpenShift CLI version based on GLIBC version
    local oc_version
    if [[ $(echo "$GLIBC_VERSION >= 2.33" | bc -l 2>/dev/null || echo "0") == "1" ]]; then
        # For GLIBC 2.33+, use latest version
        oc_version=$(wget --timeout=60 --tries=3 -O- https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/release.txt | grep 'Name:' | awk '{print $2}')
        log "INFO" "Using latest OpenShift CLI version: ${oc_version}"
    elif [[ $(echo "$GLIBC_VERSION >= 2.31" | bc -l 2>/dev/null || echo "0") == "1" ]]; then
        # For GLIBC 2.31-2.32, use version 4.12.x
        oc_version="4.12.25"
        log "INFO" "Using OpenShift CLI version compatible with GLIBC ${GLIBC_VERSION}: ${oc_version}"
    elif [[ $(echo "$GLIBC_VERSION >= 2.28" | bc -l 2>/dev/null || echo "0") == "1" ]]; then
        # For GLIBC 2.28-2.30, use version 4.11.x
        oc_version="4.11.43"
        log "INFO" "Using OpenShift CLI version compatible with GLIBC ${GLIBC_VERSION}: ${oc_version}"
    else
        # For older GLIBC versions, use version 4.10.x
        oc_version="4.10.63"
        log "INFO" "Using OpenShift CLI version compatible with GLIBC ${GLIBC_VERSION}: ${oc_version}"
    fi
    
    local oc_url="https://mirror.openshift.com/pub/openshift-v4/clients/ocp/${oc_version}/openshift-client-linux.tar.gz"
    
    # OpenShift CLI download may fail through corporate proxies due to SSL tunneling issues
    # Treat as non-critical - most Backstage development doesn't require oc
    if ! download_file "$oc_url" "/tmp/openshift-client-linux.tar.gz"; then
        log "WARN" "Failed to download OpenShift CLI (likely proxy SSL tunneling issue)"
        log "INFO" "OpenShift CLI will need to be installed manually if required"
        return 0  # Non-critical, don't fail the build
    fi
    
    if ! run_command "sudo tar xzf /tmp/openshift-client-linux.tar.gz -C /usr/local/bin oc"; then
        log "WARN" "Failed to extract OpenShift CLI"
        return 0  # Non-critical, don't fail the build
    fi
    
    run_command "rm /tmp/openshift-client-linux.tar.gz"
    log "INFO" "OpenShift CLI installed successfully"
}

install_helm() {
    log "INFO" "Installing Helm..."
    
    # Get latest Helm version
    local helm_version
    helm_version=$(wget --timeout=60 --tries=3 -O- https://get.helm.sh/helm-latest-version 2>/dev/null | grep '^v[0-9]')
    
    if [[ -z "$helm_version" ]]; then
        log "WARN" "Failed to get latest Helm version (likely proxy SSL tunneling issue)"
        log "INFO" "Helm will need to be installed manually if required"
        return 0  # Non-critical, don't fail the build
    fi
    
    log "INFO" "Installing Helm version: ${helm_version}"
    
    # Determine architecture for Helm binary
    local helm_arch
    case "$ARCH" in
        "amd64")
            helm_arch="amd64"
            ;;
        "arm64"|"aarch64")
            helm_arch="arm64"
            ;;
        "arm"|"armv7l")
            helm_arch="arm"
            ;;
        *)
            log "ERROR" "Unsupported architecture for Helm: $ARCH"
            return 1
            ;;
    esac
    
    log "INFO" "Using Helm architecture: ${helm_arch}"
    
    # Download Helm binary
    local helm_url="https://get.helm.sh/helm-${helm_version}-linux-${helm_arch}.tar.gz"
    if ! download_file "$helm_url" "/tmp/helm.tar.gz"; then
        log "WARN" "Failed to download Helm (likely proxy SSL tunneling issue)"
        log "INFO" "Helm will need to be installed manually if required"
        return 0  # Non-critical, don't fail the build
    fi
    
    # Extract and install
    if ! run_command "sudo tar xzf /tmp/helm.tar.gz -C /tmp linux-${helm_arch}/helm"; then
        log "WARN" "Failed to extract Helm"
        return 0  # Non-critical, don't fail the build
    fi
    
    if ! run_command "sudo mv /tmp/linux-${helm_arch}/helm /usr/local/bin/helm"; then
        log "WARN" "Failed to install Helm"
        return 0  # Non-critical, don't fail the build
    fi
    
    # Cleanup
    run_command "rm -rf /tmp/helm.tar.gz /tmp/linux-${helm_arch}"
    log "INFO" "Helm installed successfully"
}

install_terraform() {
    log "INFO" "Installing Terraform and TFLint..."
    
    # Add HashiCorp GPG key
    if ! run_command "sudo wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null"; then
        log "WARN" "Failed to add HashiCorp GPG key"
        log "INFO" "Terraform will need to be installed manually if required"
        return 0  # Non-critical, don't fail the build
    fi
    
    # Add HashiCorp repository
    local hashicorp_repo="deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
    if ! run_command "echo '$hashicorp_repo' | sudo tee /etc/apt/sources.list.d/hashicorp.list"; then
        log "WARN" "Failed to add HashiCorp repository"
        return 0  # Non-critical, don't fail the build
    fi
    
    # Update and install Terraform - apt update often fails through corporate proxies
    if ! run_command "sudo apt update"; then
        log "WARN" "Failed to update package lists (likely proxy authentication issue)"
        log "INFO" "Terraform will need to be installed manually if required"
        return 0  # Non-critical, don't fail the build
    fi
    
    if ! run_command "sudo apt install -y terraform"; then
        log "WARN" "Failed to install Terraform"
        log "INFO" "Terraform will need to be installed manually if required"
        return 0  # Non-critical, don't fail the build
    fi
    
    # Install TFLint
    if ! run_command "wget --timeout=60 --tries=3 -O- https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | sudo bash"; then
        log "WARN" "Failed to install TFLint (likely proxy SSL tunneling issue)"
        log "INFO" "TFLint will need to be installed manually if required"
        return 0  # Non-critical, don't fail the build
    fi
    
    log "INFO" "Terraform and TFLint installed successfully"
}

install_github_cli() {
    log "INFO" "Installing GitHub CLI (gh)..."
    
    # Ensure wget is available
    if ! check_command wget; then
        log "DEBUG" "Installing wget..."
        run_command "sudo apt update && sudo apt-get install wget -y"
    fi
    
    # Add GitHub CLI repository
    run_command "sudo mkdir -p -m 755 /etc/apt/keyrings"
    
    local temp_file
    temp_file=$(mktemp)
    
    if ! download_file "https://cli.github.com/packages/githubcli-archive-keyring.gpg" "$temp_file"; then
        log "WARN" "Failed to download GitHub CLI GPG key"
        log "INFO" "GitHub CLI will need to be installed manually if required"
        return 0  # Non-critical, don't fail the build
    fi
    
    run_command "cat $temp_file | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null"
    run_command "sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg"
    run_command "sudo mkdir -p -m 755 /etc/apt/sources.list.d"
    
    local gh_repo="deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main"
    run_command "echo '$gh_repo' | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null"
    
    # apt update often fails through corporate proxies with NTLM authentication
    if ! run_command "sudo apt update"; then
        log "WARN" "Failed to update package lists (likely proxy authentication issue)"
        log "INFO" "GitHub CLI will need to be installed manually if required"
        return 0  # Non-critical, don't fail the build
    fi
    
    if ! run_command "sudo apt install gh -y"; then
        log "WARN" "Failed to install GitHub CLI"
        log "INFO" "GitHub CLI will need to be installed manually if required"
        return 0  # Non-critical, don't fail the build
    fi
    
    run_command "rm $temp_file" || true
    log "INFO" "GitHub CLI installed successfully"
}

install_github_copilot_cli() {
    log "INFO" "Installing GitHub Copilot CLI extension (gh-copilot)..."

    # Requires GitHub CLI
    if ! check_command gh; then
        log "WARN" "GitHub CLI (gh) is not installed; skipping gh-copilot installation"
        return 0
    fi

    # Determine architecture suffix used by release artifacts
    local copilot_arch
    case "$ARCH" in
        "amd64")
            copilot_arch="x64"
            ;;
        "arm64"|"aarch64")
            copilot_arch="arm64"
            ;;
        *)
            log "WARN" "Unsupported architecture for gh-copilot: $ARCH"
            log "INFO" "gh-copilot will need to be installed manually if required"
            return 0
            ;;
    esac

    local copilot_version="0.5.0"
    local copilot_url="https://github.com/github/gh-copilot/releases/download/v${copilot_version}/gh-copilot_${copilot_version}_linux_${copilot_arch}.tar.gz"

    # GitHub release downloads can fail behind corporate proxies; treat as non-critical
    if ! run_command "type curl >/dev/null && sudo curl -sSL ${copilot_url} | sudo tar -xz -C /usr/local/bin --strip-components=1"; then
        log "WARN" "Failed to install gh-copilot (likely proxy SSL tunneling issue)"
        log "INFO" "gh-copilot will need to be installed manually if required"
        return 0
    fi

    if ! run_command "gh copilot version"; then
        log "WARN" "gh-copilot installed but version check failed"
        log "INFO" "You may need to authenticate gh before using Copilot CLI"
        return 0
    fi

    log "INFO" "GitHub Copilot CLI extension installed successfully"
}

install_docker_cli() {
    log "INFO" "Installing Docker CLI..."

    # Ensure prerequisites are available
    if ! run_command "sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg"; then
        log "WARN" "Failed to install Docker CLI prerequisites"
        log "INFO" "Docker CLI will need to be installed manually if required"
        return 0
    fi

    if ! run_command "sudo install -m 0755 -d /etc/apt/keyrings"; then
        log "WARN" "Failed to create apt keyrings directory"
        return 0
    fi

    if ! run_command "sudo sh -c 'curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg'"; then
        log "WARN" "Failed to add Docker GPG key"
        log "INFO" "Docker CLI will need to be installed manually if required"
        return 0
    fi

    if ! run_command "sudo chmod a+r /etc/apt/keyrings/docker.gpg"; then
        log "WARN" "Failed to set Docker key permissions"
        return 0
    fi

    local docker_repo="deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable"
    if ! run_command "echo '$docker_repo' | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null"; then
        log "WARN" "Failed to add Docker apt repository"
        return 0
    fi

    if ! run_command "sudo apt-get update"; then
        log "WARN" "Failed to update apt package lists for Docker CLI"
        return 0
    fi

    if ! run_command "sudo apt-get install -y docker-ce-cli docker-buildx-plugin docker-compose-plugin"; then
        log "WARN" "Failed to install Docker CLI packages"
        log "INFO" "Docker CLI will need to be installed manually if required"
        return 0
    fi

    log "INFO" "Docker CLI installed successfully"
}

install_specify_cli() {
    log "INFO" "Installing specify-cli via uv..."

    # Check if uv is available
    if ! check_command uv; then
        log "WARN" "uv is not installed; skipping specify-cli installation"
        log "INFO" "specify-cli requires uv to be installed. Install uv first if needed."
        return 0
    fi

    # Install specify-cli from GitHub
    if ! run_command "uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v0.8.12"; then
        log "WARN" "Failed to install specify-cli"
        log "INFO" "specify-cli will need to be installed manually if required"
        return 0
    fi

    log "INFO" "specify-cli installed successfully"
}

# =============================================================================
# Verification Functions
# =============================================================================
verify_installations() {
    log "INFO" "Verifying installations..."
    
    # Critical tools that must be installed
    local critical_tools=(
        "sqlcmd"
        "bcp"
    )
    
    # Optional tools that may fail due to proxy/network issues
    local optional_tools=(
        "az"
        "kubectl"
        "kubelogin"
        "docker"
        "oc"
        "helm"
        "terraform"
        "tflint"
        "gh"
        "gh-copilot"
        "specify"
    )
    
    # Add Chrome to optional verification only on Linux AMD64
    if [[ "$(uname)" == "Linux" ]] && [[ "$ARCH" == "amd64" ]]; then
        optional_tools+=("google-chrome")
    fi
    
    local failed_critical=()
    local failed_optional=()
    
    # Check critical tools
    for tool in "${critical_tools[@]}"; do
        if check_command "$tool"; then
            local version
            version=$($tool --version 2>/dev/null | head -n1 || echo "version unknown")
            log "INFO" "✓ $tool: $version"
        else
            log "ERROR" "✗ $tool: not found (CRITICAL)"
            failed_critical+=("$tool")
        fi
    done
    
    # Check optional tools
    for tool in "${optional_tools[@]}"; do
        if check_command "$tool"; then
            local version
            if [[ "$tool" == "gh-copilot" ]]; then
                version=$(gh copilot version 2>/dev/null | head -n1 || echo "version unknown")
            else
                version=$($tool --version 2>/dev/null | head -n1 || echo "version unknown")
            fi
            log "INFO" "✓ $tool: $version"
        else
            log "WARN" "✗ $tool: not found (optional)"
            failed_optional+=("$tool")
        fi
    done
    
    if [[ ${#failed_optional[@]} -gt 0 ]]; then
        log "WARN" "Optional tools not installed (can be installed manually later): ${failed_optional[*]}"
    fi
    
    if [[ ${#failed_critical[@]} -gt 0 ]]; then
        log "ERROR" "Critical tools failed to install: ${failed_critical[*]}"
        return 1
    else
        log "INFO" "All critical tools installed successfully!"
        return 0
    fi
}

# =============================================================================
# Cleanup Functions
# =============================================================================
cleanup() {
    log "DEBUG" "Cleaning up temporary files..."
    run_command "rm -rf $TEMP_DIR" || true
    run_command "sudo apt-get clean" || true
    run_command "sudo apt-get autoremove -y" || true
}

# =============================================================================
# Main Function
# =============================================================================
main() {
    log "INFO" "Starting Dev Container Tools Installation"
    log "INFO" "Log file: $LOG_FILE"
    
    # Create temp directory
    mkdir -p "$TEMP_DIR"
    
    # Detect system
    detect_system
    
    # Install tools
    local install_functions=(
        "install_specify_cli"
        "install_chrome"
        "install_sql_server_tools"
        "install_azure_cli"
        "install_docker_cli"
        # "install_openshift_cli"
        # "install_helm"
        # "install_terraform"
        "install_github_cli"
        "install_github_copilot_cli"
    )
    
    # Add GCM only for AMD64 architecture
    if [[ "$ARCH" == "amd64" ]]; then
        install_functions+=("install_git_credential_manager")
    else
        log "INFO" "Skipping Git Credential Manager (not available for $ARCH Linux)"
    fi
    
    local failed_installations=()
    
    for func in "${install_functions[@]}"; do
        log "INFO" "Running $func..."
        if ! $func; then
            log "ERROR" "$func failed"
            failed_installations+=("$func")
        fi
    done
    
    # Verify installations
    local verification_result=0
    if ! verify_installations; then
        verification_result=1
    fi
    
    # Cleanup
    cleanup
    
    # Final status
    if [[ ${#failed_installations[@]} -gt 0 ]] || [[ $verification_result -ne 0 ]]; then
        log "ERROR" "Installation completed with errors."
        if [[ ${#failed_installations[@]} -gt 0 ]]; then
            log "ERROR" "Failed installations: ${failed_installations[*]}"
        fi
        if [[ $verification_result -ne 0 ]]; then
            log "ERROR" "Some tools failed verification"
        fi
        log "INFO" "Check log file for details: $LOG_FILE"
        exit 1
    else
        log "INFO" "Installation completed successfully!"
        log "INFO" "Log file: $LOG_FILE"
    fi
}

# =============================================================================
# Script Execution
# =============================================================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
