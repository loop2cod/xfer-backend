#!/usr/bin/env python3
"""
Script to verify all endpoints return success field
"""

import ast
import os
from pathlib import Path

def check_endpoint_file(file_path):
    """Check if all endpoints in a file return BaseResponse or MessageResponse"""
    print(f"\n=== Checking {file_path.name} ===")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if BaseResponse and MessageResponse are imported
    has_base_import = "BaseResponse" in content and "MessageResponse" in content
    print(f"✓ Has BaseResponse/MessageResponse imports: {has_base_import}")
    
    # Parse the file to find all router decorators and their functions
    try:
        tree = ast.parse(content)
        
        endpoints = []
        current_decorator = None
        
        for node in ast.walk(tree):
            # Look for decorator usage
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if (isinstance(decorator, ast.Call) and 
                        isinstance(decorator.func, ast.Attribute) and
                        isinstance(decorator.func.value, ast.Name) and
                        decorator.func.value.id == "router"):
                        
                        # Extract method and path
                        method = decorator.func.attr
                        path = None
                        response_model = None
                        
                        if decorator.args:
                            if isinstance(decorator.args[0], ast.Constant):
                                path = decorator.args[0].value
                        
                        # Check for response_model in keywords
                        for keyword in decorator.keywords:
                            if keyword.arg == "response_model":
                                if isinstance(keyword.value, ast.Subscript):
                                    if isinstance(keyword.value.value, ast.Name):
                                        response_model = keyword.value.value.id
                                elif isinstance(keyword.value, ast.Name):
                                    response_model = keyword.value.id
                        
                        endpoints.append({
                            'function': node.name,
                            'method': method,
                            'path': path,
                            'response_model': response_model
                        })
        
        print(f"Found {len(endpoints)} endpoints:")
        
        success_format_count = 0
        for ep in endpoints:
            has_success_format = ep['response_model'] in ['BaseResponse', 'MessageResponse']
            status = "✓" if has_success_format else "✗"
            print(f"  {status} {ep['method'].upper()} {ep['path']} -> {ep['response_model']}")
            if has_success_format:
                success_format_count += 1
        
        print(f"\nSummary: {success_format_count}/{len(endpoints)} endpoints use success format")
        return success_format_count == len(endpoints)
    
    except Exception as e:
        print(f"Error parsing file: {e}")
        return False

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
    print("=" * 50)
    
    all_correct = True
    total_endpoints = 0
    correct_endpoints = 0
    
    for file_path in endpoint_files:
        if file_path.exists():
            file_correct = check_endpoint_file(file_path)
            all_correct = all_correct and file_correct
        else:
            print(f"❌ File not found: {file_path}")
            all_correct = False
    
    print("\n" + "=" * 50)
    if all_correct:
        print("🎉 SUCCESS: All endpoints properly return success field!")
        print("\nAll endpoints now return either:")
        print("  • BaseResponse[T] - for data responses with success: true/false")
        print("  • MessageResponse - for simple messages with success: true/false")
    else:
        print("❌ Some endpoints still need to be updated")
    
    print("\nResponse format examples:")
    print("1. Data response: { success: true, data: {...}, message: '...' }")
    print("2. Message response: { success: true, message: '...' }")
    print("3. Error response: { success: false, error: '...', message: '...' }")

if __name__ == "__main__":
    main()