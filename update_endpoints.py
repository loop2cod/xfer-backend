#!/usr/bin/env python3
"""
Script to update all endpoints to include success field in responses
"""

import os
import re
from pathlib import Path

# Define the base directory
BASE_DIR = Path(__file__).parent / "app" / "api" / "v1" / "endpoints"

def add_imports(content):
    """Add necessary imports if not present"""
    if "from app.schemas.base import BaseResponse, MessageResponse" not in content:
        # Find where to insert the import
        lines = content.split('\n')
        insert_index = 0
        
        # Find the last import line
        for i, line in enumerate(lines):
            if line.startswith('from app.schemas') or line.startswith('from app.models'):
                insert_index = i + 1
        
        # Insert the import
        lines.insert(insert_index, "from app.schemas.base import BaseResponse, MessageResponse")
        content = '\n'.join(lines)
    
    return content

def update_response_models(content):
    """Update response models in endpoint decorators"""
    # Update List response models
    content = re.sub(
        r'response_model=List\[([^\]]+)\]',
        r'response_model=BaseResponse[List[\1]]',
        content
    )
    
    # Update single response models (but not if already wrapped in BaseResponse)
    content = re.sub(
        r'response_model=(?!BaseResponse)([^,\)]+)',
        r'response_model=BaseResponse[\1]',
        content
    )
    
    # Handle endpoints that return simple dict messages
    content = re.sub(
        r'(@router\.[a-z]+\("[^"]*")\)',
        r'\1, response_model=MessageResponse)',
        content
    )
    
    return content

def update_return_statements(content):
    """Update return statements to use BaseResponse"""
    
    # Handle simple message returns
    content = re.sub(
        r'return \{"message": "([^"]+)"\}',
        r'return MessageResponse.success_message("\1")',
        content
    )
    
    content = re.sub(
        r'return \{"message": f"([^"]+)"\}',
        r'return MessageResponse.success_message(f"\1")',
        content
    )
    
    # Handle complex dictionary returns
    content = re.sub(
        r'return \{([^}]+)\}',
        lambda m: f'return BaseResponse.success_response(data={{{m.group(1)}}}, message="Operation completed successfully")',
        content
    )
    
    return content

def wrap_model_returns(content):
    """Wrap direct model returns with BaseResponse"""
    
    # Find return statements that return models directly
    patterns = [
        (r'return (user)', r'return BaseResponse.success_response(data=\1, message="User operation completed successfully")'),
        (r'return (admin)', r'return BaseResponse.success_response(data=\1, message="Admin operation completed successfully")'),  
        (r'return (users)', r'return BaseResponse.success_response(data=\1, message="Users retrieved successfully")'),
        (r'return (admins)', r'return BaseResponse.success_response(data=\1, message="Admins retrieved successfully")'),
        (r'return (transfer)', r'return BaseResponse.success_response(data=\1, message="Transfer operation completed successfully")'),
        (r'return (transfers)', r'return BaseResponse.success_response(data=\1, message="Transfers retrieved successfully")'),
        (r'return (wallet)', r'return BaseResponse.success_response(data=\1, message="Wallet operation completed successfully")'), 
        (r'return (wallets)', r'return BaseResponse.success_response(data=\1, message="Wallets retrieved successfully")'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    return content

def update_endpoint_file(file_path):
    """Update a single endpoint file"""
    print(f"Processing {file_path}...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Apply transformations
    content = add_imports(content)
    content = update_response_models(content)
    content = update_return_statements(content)
    content = wrap_model_returns(content)
    
    # Only write if content changed
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Main function to update all endpoint files"""
    endpoint_files = [
        "users.py",
        "transfers.py", 
        "wallets.py",
        "admin.py"
    ]
    
    for filename in endpoint_files:
        file_path = BASE_DIR / filename
        if file_path.exists():
            try:
                changed = update_endpoint_file(file_path)
                if changed:
                    print(f"✓ Updated {filename}")
                else:
                    print(f"- No changes needed for {filename}")
            except Exception as e:
                print(f"✗ Error updating {filename}: {e}")
        else:
            print(f"✗ File not found: {filename}")

if __name__ == "__main__":
    main()