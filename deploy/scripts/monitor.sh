#!/bin/bash

# KeyPick Monitoring Script
# Monitor Fly.io and Cloudflare deployments

echo "📊 KeyPick Monitoring Dashboard"
echo "==============================="

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check Fly.io status
check_fly() {
    echo ""
    echo "🦅 Fly.io Status"
    echo "----------------"

    if fly status &> /dev/null; then
        fly status
        echo ""
        echo "Recent logs:"
        fly logs --limit 10
    else
        echo -e "${RED}❌ Fly app not found or not logged in${NC}"
    fi
}

# Check Cloudflare status
check_cloudflare() {
    echo ""
    echo "☁️ Cloudflare Workers Status"
    echo "---------------------------"

    read -p "Enter Worker URL: " worker_url

    if [[ ! -z "$worker_url" ]]; then
        response=$(curl -s -w "\n%{http_code}" "https://$worker_url/health")
        status_code=$(echo "$response" | tail -n 1)
        body=$(echo "$response" | head -n -1)

        if [[ "$status_code" == "200" ]]; then
            echo -e "${GREEN}✅ Worker is healthy${NC}"
            echo "$body" | jq .
        else
            echo -e "${RED}❌ Worker unhealthy (HTTP $status_code)${NC}"
        fi

        # Show recent requests
        echo ""
        echo "Recent requests (live tail):"
        echo "Press Ctrl+C to stop"
        wrangler tail
    fi
}

# Performance test
perf_test() {
    echo ""
    echo "⚡ Performance Test"
    echo "------------------"

    read -p "Enter API endpoint URL: " api_url
    read -p "Enter API key: " api_key
    read -p "Number of requests (default 10): " num_requests

    num_requests=${num_requests:-10}

    echo "Running $num_requests requests..."

    total_time=0
    success_count=0
    fail_count=0

    for i in $(seq 1 $num_requests); do
        start_time=$(date +%s%N)

        response=$(curl -s -w "\n%{http_code}" "$api_url" \
            -H "X-API-Key: $api_key")
        status_code=$(echo "$response" | tail -n 1)

        end_time=$(date +%s%N)
        elapsed=$((($end_time - $start_time) / 1000000))

        if [[ "$status_code" == "200" ]]; then
            echo -e "${GREEN}✓${NC} Request $i: ${elapsed}ms"
            success_count=$((success_count + 1))
        else
            echo -e "${RED}✗${NC} Request $i: HTTP $status_code"
            fail_count=$((fail_count + 1))
        fi

        total_time=$((total_time + elapsed))
    done

    avg_time=$((total_time / num_requests))

    echo ""
    echo "Results:"
    echo "--------"
    echo -e "Success: ${GREEN}$success_count${NC}"
    echo -e "Failed: ${RED}$fail_count${NC}"
    echo "Average response time: ${avg_time}ms"
}

# Resource usage
resource_usage() {
    echo ""
    echo "💾 Resource Usage"
    echo "----------------"

    echo "Fly.io:"
    fly scale show

    echo ""
    echo "Cloudflare (last 24h):"
    echo "Check dashboard: https://dash.cloudflare.com/workers-and-pages"
}

# Main menu
while true; do
    echo ""
    echo "Select monitoring option:"
    echo "1) Check all status"
    echo "2) Fly.io status"
    echo "3) Cloudflare status"
    echo "4) Performance test"
    echo "5) Resource usage"
    echo "6) Exit"

    read -p "Choice: " choice

    case $choice in
        1)
            check_fly
            check_cloudflare
            ;;
        2)
            check_fly
            ;;
        3)
            check_cloudflare
            ;;
        4)
            perf_test
            ;;
        5)
            resource_usage
            ;;
        6)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            ;;
    esac
done