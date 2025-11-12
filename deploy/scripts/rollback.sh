#!/bin/bash

# KeyPick Rollback Script
# Rollback Fly.io and Cloudflare deployments

set -e

echo "🔄 KeyPick Rollback Script"
echo "=========================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Rollback Fly.io
rollback_fly() {
    echo ""
    echo "🦅 Rolling back Fly.io..."

    cd ../..

    # Show releases
    echo "Recent releases:"
    fly releases

    read -p "Enter version number to rollback to (e.g., v10): " version

    if [[ ! -z "$version" ]]; then
        fly deploy --image "registry.fly.io/keypick:$version"
        echo -e "${GREEN}✅ Rolled back to $version${NC}"
    else
        echo -e "${YELLOW}⚠️ No version specified, skipping${NC}"
    fi

    cd deploy/scripts
}

# Rollback Cloudflare (manual process)
rollback_cloudflare() {
    echo ""
    echo "☁️ Cloudflare Workers Rollback"
    echo ""
    echo -e "${YELLOW}Cloudflare rollback must be done manually:${NC}"
    echo "1. Go to Cloudflare Dashboard"
    echo "2. Navigate to Workers & Pages > keypick-gateway"
    echo "3. Go to Deployments tab"
    echo "4. Find the previous deployment"
    echo "5. Click 'Rollback to this deployment'"
    echo ""
    read -p "Press Enter when complete..."
}

# Main menu
echo ""
echo "Select rollback option:"
echo "1) Rollback both (Fly.io + Cloudflare)"
echo "2) Rollback Fly.io only"
echo "3) Rollback Cloudflare only (manual)"
echo "4) Exit"

read -p "Choice: " choice

case $choice in
    1)
        rollback_fly
        rollback_cloudflare
        ;;
    2)
        rollback_fly
        ;;
    3)
        rollback_cloudflare
        ;;
    4)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Rollback complete!${NC}"