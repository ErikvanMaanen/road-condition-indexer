import os
import glob

def fix_test_imports():
    """Add parent directory to Python path in all test files."""
    
    test_files = glob.glob("tests/test_*.py")
    
    path_fix = """import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
    
    for test_file in test_files:
        if test_file == "tests/test_runner.py":
            continue
            
        print(f"Fixing {test_file}...")
        
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if already has the fix
            if "sys.path.insert(0" in content:
                print(f"  Already fixed: {test_file}")
                continue
                
            # Find the first import
            lines = content.split('\n')
            first_import_idx = -1
            
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    first_import_idx = i
                    break
            
            if first_import_idx == -1:
                print(f"  No imports found in {test_file}")
                continue
            
            # Insert the path fix before the first import
            lines.insert(first_import_idx, path_fix.strip())
            
            # Write back
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
                
            print(f"  Fixed: {test_file}")
            
        except Exception as e:
            print(f"  Error fixing {test_file}: {e}")

if __name__ == "__main__":
    fix_test_imports()
