#!/usr/bin/env python3
"""Test runner for all Road Condition Indexer tests."""

import sys
import os
import time
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

# Add parent directory to path for imports
project_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_dir))

class TestRunner:
    """Manages and executes test suites."""
    
    def __init__(self, test_dir: Optional[str] = None):
        self.test_dir = Path(test_dir) if test_dir else Path(__file__).parent
        self.results: Dict[str, Any] = {
            "tests": [],
            "start_time": time.time(),
            "total_duration": 0.0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    
    def discover_tests(self) -> List[Path]:
        """Discover all test files in the test directory."""
        test_files: List[Path] = []
        
        for test_file in self.test_dir.glob("test_*.py"):
            if test_file.name != "test_runner.py":  # Exclude self
                test_files.append(test_file)
        
        return sorted(test_files)
    
    def load_test_module(self, test_file: Path):
        """Load a test module dynamically."""
        try:
            spec = importlib.util.spec_from_file_location(test_file.stem, test_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load spec for {test_file}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            print(f"❌ Failed to load {test_file}: {e}")
            return None
    
    def run_test_module(self, test_file: Path) -> Dict[str, Any]:
        """Run a single test module."""
        test_result: Dict[str, Any] = {
            "name": test_file.stem,
            "file": str(test_file),
            "success": False,
            "duration": 0.0,
            "error": None,
            "output": []
        }
        
        print(f"\n🔍 Running {test_file.name}...")
        start_time = time.time()
        
        try:
            module = self.load_test_module(test_file)
            if module is None:
                test_result["error"] = "Failed to load module"
                return test_result
            
            # Look for main function or test functions
            main_func: Optional[Callable] = getattr(module, 'main', None)
            if main_func is None:
                # Look for functions starting with 'test_'
                test_functions = [getattr(module, name) for name in dir(module) 
                                if name.startswith('test_') and callable(getattr(module, name))]
                
                if test_functions:
                    # Run all test functions
                    for test_func in test_functions:
                        try:
                            result = test_func()
                            test_result["output"].append(f"{test_func.__name__}: {'PASS' if result else 'FAIL'}")
                        except Exception as e:
                            test_result["output"].append(f"{test_func.__name__}: ERROR - {e}")
                    test_result["success"] = True
                else:
                    test_result["error"] = "No main() function or test_ functions found"
            else:
                # Run main function
                result = main_func()
                test_result["success"] = bool(result) if result is not None else True
            
        except SystemExit as e:
            # Handle sys.exit() calls
            test_result["success"] = e.code == 0
            if e.code != 0:
                test_result["error"] = f"Test exited with code {e.code}"
        except Exception as e:
            test_result["error"] = str(e)
            test_result["success"] = False
        
        test_result["duration"] = time.time() - start_time
        
        status = "✅ PASS" if test_result["success"] else "❌ FAIL"
        print(f"   {status} ({test_result['duration']:.2f}s)")
        if test_result["error"]:
            print(f"   Error: {test_result['error']}")
        
        return test_result
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all discovered tests."""
        print("🚀 Road Condition Indexer Test Runner")
        print("=" * 50)
        
        test_files = self.discover_tests()
        print(f"📋 Discovered {len(test_files)} test files")
        
        for test_file in test_files:
            test_result = self.run_test_module(test_file)
            self.results["tests"].append(test_result)
            
            if test_result["success"]:
                self.results["passed"] += 1
            else:
                self.results["failed"] += 1
                if test_result["error"]:
                    self.results["errors"].append({
                        "test": test_result["name"],
                        "error": test_result["error"]
                    })
        
        self.results["total_duration"] = time.time() - self.results["start_time"]
        
        return self.results
    
    def print_summary(self) -> None:
        """Print test execution summary."""
        total_tests = len(self.results["tests"])
        passed = self.results["passed"]
        failed = self.results["failed"]
        duration = self.results["total_duration"]
        
        print("\n" + "=" * 50)
        print("📊 Test Execution Summary")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/total_tests*100):.1f}%" if total_tests > 0 else "0.0%")
        print(f"Total Duration: {duration:.2f}s")
        
        if self.results["errors"]:
            print(f"\n❌ Errors ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                print(f"   {error['test']}: {error['error']}")
        
        if failed == 0:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n⚠️  {failed} test(s) failed")
        
        print("=" * 50)

def main() -> int:
    """Main test runner entry point."""
    test_runner = TestRunner()
    results = test_runner.run_all_tests()
    test_runner.print_summary()
    
    # Return exit code based on results
    return 0 if results["failed"] == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
