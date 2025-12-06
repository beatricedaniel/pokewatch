#!/bin/bash
# Version management script for PokeWatch
# Usage:
#   ./version.sh current          # Show current version
#   ./version.sh bump patch        # Bump patch version (1.0.0 -> 1.0.1)
#   ./version.sh bump minor        # Bump minor version (1.0.0 -> 1.1.0)
#   ./version.sh bump major        # Bump major version (1.0.0 -> 2.0.0)
#   ./version.sh set 1.2.3         # Set specific version

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYPROJECT_FILE="$PROJECT_ROOT/pyproject.toml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get current version from pyproject.toml
get_current_version() {
    if [ -f "$PYPROJECT_FILE" ]; then
        grep -E '^version = ' "$PYPROJECT_FILE" | sed 's/version = "\(.*\)"/\1/'
    else
        echo "0.1.0"
    fi
}

# Get latest git tag
get_latest_tag() {
    git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0"
}

# Update version in pyproject.toml
update_pyproject_version() {
    local new_version=$1
    if [ -f "$PYPROJECT_FILE" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/^version = .*/version = \"$new_version\"/" "$PYPROJECT_FILE"
        else
            # Linux
            sed -i "s/^version = .*/version = \"$new_version\"/" "$PYPROJECT_FILE"
        fi
        echo -e "${GREEN}✓ Updated pyproject.toml to version $new_version${NC}"
    fi
}

# Parse version string into components
parse_version() {
    local version=$1
    # Remove 'v' prefix if present
    version=${version#v}

    IFS='.' read -r major minor patch <<< "$version"
    echo "$major $minor $patch"
}

# Bump version
bump_version() {
    local bump_type=$1
    local current_version=$(get_current_version)

    read -r major minor patch <<< $(parse_version "$current_version")

    case $bump_type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        *)
            echo -e "${RED}Error: Invalid bump type. Use 'major', 'minor', or 'patch'${NC}"
            exit 1
            ;;
    esac

    local new_version="$major.$minor.$patch"
    echo "$new_version"
}

# Create git tag
create_tag() {
    local version=$1
    local tag="v$version"

    echo -e "${YELLOW}Creating git tag: $tag${NC}"

    git tag -a "$tag" -m "Release version $version"

    echo -e "${GREEN}✓ Created tag $tag${NC}"
    echo -e "${YELLOW}Push tag with: git push origin $tag${NC}"
}

# Show current version info
show_current() {
    local file_version=$(get_current_version)
    local git_tag=$(get_latest_tag)

    echo "=== Version Information ==="
    echo "pyproject.toml: $file_version"
    echo "Latest git tag: $git_tag"
    echo ""

    if [ "v$file_version" != "$git_tag" ]; then
        echo -e "${YELLOW}⚠ Warning: File version and git tag don't match${NC}"
    else
        echo -e "${GREEN}✓ File version and git tag are in sync${NC}"
    fi
}

# Main script logic
case "${1:-}" in
    current)
        show_current
        ;;

    bump)
        if [ -z "${2:-}" ]; then
            echo -e "${RED}Error: Specify bump type (major, minor, or patch)${NC}"
            exit 1
        fi

        current_version=$(get_current_version)
        echo "Current version: $current_version"

        new_version=$(bump_version "$2")
        echo "New version: $new_version"

        read -p "Update to version $new_version? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            update_pyproject_version "$new_version"
            create_tag "$new_version"
        else
            echo "Cancelled"
            exit 0
        fi
        ;;

    set)
        if [ -z "${2:-}" ]; then
            echo -e "${RED}Error: Specify version number (e.g., 1.2.3)${NC}"
            exit 1
        fi

        new_version="${2#v}"  # Remove 'v' prefix if present

        # Validate version format
        if ! [[ "$new_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo -e "${RED}Error: Invalid version format. Use X.Y.Z (e.g., 1.2.3)${NC}"
            exit 1
        fi

        echo "Setting version to: $new_version"

        read -p "Continue? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            update_pyproject_version "$new_version"
            create_tag "$new_version"
        else
            echo "Cancelled"
            exit 0
        fi
        ;;

    *)
        echo "Usage: $0 {current|bump|set}"
        echo ""
        echo "Commands:"
        echo "  current          Show current version information"
        echo "  bump TYPE        Bump version (TYPE: major, minor, or patch)"
        echo "  set VERSION      Set specific version (e.g., 1.2.3)"
        echo ""
        echo "Examples:"
        echo "  $0 current"
        echo "  $0 bump patch"
        echo "  $0 bump minor"
        echo "  $0 bump major"
        echo "  $0 set 1.2.3"
        exit 1
        ;;
esac
