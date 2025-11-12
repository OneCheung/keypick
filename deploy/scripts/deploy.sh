#!/bin/bash

# KeyPick Production Deployment Script
# Deploys to Cloudflare Workers + Fly.io

set -e

echo "🚀 KeyPick Deployment Script"
echo "============================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check required tools
check_tools() {
    echo "📋 Checking required tools..."

    if ! command -v fly &> /dev/null; then
        echo -e "${RED}❌ Fly CLI not found${NC}"
        echo "Install: curl -L https://fly.io/install.sh | sh"
        exit 1
    fi

    if ! command -v wrangler &> /dev/null; then
        echo -e "${RED}❌ Wrangler not found${NC}"
        echo "Install: npm install -g wrangler"
        exit 1
    fi

    echo -e "${GREEN}✅ All tools installed${NC}"
}

# Deploy to Fly.io
deploy_fly() {
    echo ""
    echo "🦅 Deploying to Fly.io..."

    cd ../..

    # Check if app exists
    if fly status &> /dev/null; then
        echo "App exists, deploying update..."
        fly deploy
    else
        echo "Creating new Fly app..."
        fly launch --name keypick --region sin --no-deploy

        echo "Setting secrets..."
        read -p "Enter KEYPICK_API_KEYS (comma-separated): " api_keys
        fly secrets set KEYPICK_API_KEYS="$api_keys"

        read -p "Enter INTERNAL_KEY: " internal_key
        fly secrets set INTERNAL_KEY="$internal_key"

        # Optional Supabase
        read -p "Configure Supabase? (y/n): " config_supabase
        if [[ $config_supabase == "y" ]]; then
            read -p "Enter SUPABASE_URL: " supabase_url
            fly secrets set SUPABASE_URL="$supabase_url"

            read -p "Enter SUPABASE_ANON_KEY: " supabase_key
            fly secrets set SUPABASE_ANON_KEY="$supabase_key"
        fi

        # Create volume
        fly volumes create keypick_data --region sin --size 1

        # Deploy
        fly deploy
    fi

    # Get app URL
    FLY_URL=$(fly info -j | grep -o '"Hostname":"[^"]*' | grep -o '[^"]*$')
    echo -e "${GREEN}✅ Fly.io deployed at: https://$FLY_URL${NC}"

    cd deploy/scripts
}

# Deploy to Cloudflare
deploy_cloudflare() {
    echo ""
    echo "☁️ Deploying to Cloudflare Workers..."

    cd ../cloudflare

    # Check if logged in
    if ! wrangler whoami &> /dev/null; then
        echo "Please login to Cloudflare:"
        wrangler login
    fi

    # Create KV namespace if needed
    if ! grep -q "YOUR_KV_NAMESPACE_ID" wrangler.toml; then
        echo "KV namespace already configured"
    else
        echo "Creating KV namespace..."
        KV_ID=$(wrangler kv:namespace create "CACHE" --preview=false | grep -o 'id = "[^"]*' | grep -o '[^"]*$')
        KV_PREVIEW_ID=$(wrangler kv:namespace create "CACHE" --preview | grep -o 'preview_id = "[^"]*' | grep -o '[^"]*$')

        # Update wrangler.toml
        sed -i.bak "s/YOUR_KV_NAMESPACE_ID/$KV_ID/" wrangler.toml
        sed -i.bak "s/YOUR_KV_PREVIEW_ID/$KV_PREVIEW_ID/" wrangler.toml
        rm wrangler.toml.bak
    fi

    # Update backend URL
    if [[ ! -z "$FLY_URL" ]]; then
        sed -i.bak "s|https://keypick.fly.dev|https://$FLY_URL|" wrangler.toml
        rm wrangler.toml.bak
    fi

    # Set secrets
    echo "Setting Cloudflare secrets..."
    read -p "Enter KEYPICK_API_KEYS (comma-separated): " cf_api_keys
    echo "$cf_api_keys" | wrangler secret put KEYPICK_API_KEYS

    read -p "Enter INTERNAL_KEY (same as Fly.io): " cf_internal_key
    echo "$cf_internal_key" | wrangler secret put INTERNAL_KEY

    # Deploy
    wrangler deploy --env production

    echo -e "${GREEN}✅ Cloudflare Worker deployed${NC}"

    cd ../scripts
}

# Test deployment
test_deployment() {
    echo ""
    echo "🧪 Testing deployment..."

    read -p "Enter your Worker URL (e.g., keypick-gateway.account.workers.dev): " worker_url
    read -p "Enter an API key for testing: " test_api_key

    # Test health check
    echo "Testing health check..."
    curl -s "https://$worker_url/health" | jq .

    # Test API with auth
    echo ""
    echo "Testing authenticated API..."
    curl -s "https://$worker_url/api/crawl/platforms" \
        -H "X-API-Key: $test_api_key" | jq .

    echo -e "${GREEN}✅ Tests complete${NC}"
}

# Main menu
main_menu() {
    echo ""
    echo "Select deployment option:"
    echo "1) Full deployment (Fly.io + Cloudflare)"
    echo "2) Fly.io only"
    echo "3) Cloudflare only"
    echo "4) Test deployment"
    echo "5) Exit"

    read -p "Choice: " choice

    case $choice in
        1)
            check_tools
            deploy_fly
            deploy_cloudflare
            test_deployment
            ;;
        2)
            check_tools
            deploy_fly
            ;;
        3)
            check_tools
            deploy_cloudflare
            ;;
        4)
            test_deployment
            ;;
        5)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            main_menu
            ;;
    esac
}

# Run
main_menu

echo ""
echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Test your API endpoints"
echo "2. Configure Dify to use the production API"
echo "3. Set up monitoring and alerts"
echo ""
echo "Documentation: DEPLOY_GUIDE.md"