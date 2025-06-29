#!/usr/bin/env python3
"""
Simple verification script to check endpoint success formats
"""

import re
from pathlib import Path

def check_file_endpoints(file_path):
    """Check endpoints in a single file"""
    print(f"\n=== Checking {file_path.name} ===")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find all router decorators
    router_pattern = r'@router\.(get|post|put|delete|patch)\("([^"]*)"(?:, response_model=([^)]+))?\)'
    matches = re.findall(router_pattern, content)
    
    print(f"Found {len(matches)} endpoints:")
    
    success_count = 0
    for method, path, response_model in matches:
        # Check if using BaseResponse or MessageResponse
        uses_success_format = (
            "BaseResponse" in response_model or 
            "MessageResponse" in response_model
        ) if response_model else False
        
        status = "✓" if uses_success_format else "✗"
        print(f"  {status} {method.upper()} {path} -> {response_model or 'No model specified'}")
        
        if uses_success_format:
            success_count += 1
    
    print(f"Summary: {success_count}/{len(matches)} endpoints use success format")
    return success_count, len(matches)

def main():
    """Check all endpoint files"""
    
    endpoint_files = [
        Path("/Users/nizam/Documents/George/xfer-monitor/backend/app/api/v1/endpoints/auth.py"),
        Path("/Users/nizam/Documents/George/xfer-monitor/backend/app/api/v1/endpoints/users.py"),
        Path("/Users/nizam/Documents/George/xfer-monitor/backend/app/api/v1/endpoints/transfers.py"),
        Path("/Users/nizam/Documents/George/xfer-monitor/backend/app/api/v1/endpoints/wallets.py"),
        Path("/Users/nizam/Documents/George/xfer-monitor/backend/app/api/v1/endpoints/admin.py"),
    ]
    
    print("🔍 Verifying all endpoints return success field...")
    print("=" * 60)
    
    total_success = 0
    total_endpoints = 0
    
    for file_path in endpoint_files:
        if file_path.exists():
            success, total = check_file_endpoints(file_path)
            total_success += success
            total_endpoints += total
        else:
            print(f"❌ File not found: {file_path}")
    
    print("\n" + "=" * 60)
    print(f"OVERALL SUMMARY: {total_success}/{total_endpoints} endpoints use success format")
    
    if total_success == total_endpoints:
        print("🎉 SUCCESS: All endpoints properly return success field!")
    else:
        print(f"❌ {total_endpoints - total_success} endpoints still need to be updated")
    
    success_rate = (total_success / total_endpoints * 100) if total_endpoints > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")
    
    print("\nResponse format standards:")
    print("✓ BaseResponse[T] - for data responses")
    print("✓ MessageResponse - for simple messages")
    print("✓ Both include success: true/false field")

if __name__ == "__main__":
    main()