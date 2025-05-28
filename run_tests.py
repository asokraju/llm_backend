#!/usr/bin/env python3
"""
LightRAG Backend Test Runner

This script provides a comprehensive test suite runner with service health checks,
detailed reporting, and various test execution options.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit            # Run only unit tests
    python run_tests.py --integration     # Run only integration tests
    python run_tests.py --infrastructure  # Run only infrastructure tests
    python run_tests.py -v                # Verbose output
    python run_tests.py --coverage        # Generate coverage report
"""

import argparse
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple
import requests
import json

# ANSI color codes
COLORS = {
    'GREEN': '\033[92m',
    'RED': '\033[91m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'BOLD': '\033[1m',
    'RESET': '\033[0m'
}

class TestRunner:
    """Main test runner class."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.test_suites = {
            'unit': 'tests/unit',
            'integration': 'tests/integration',
            'infrastructure': 'tests/infrastructure'
        }
        self.results = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'total': 0
        }
        
    def print_header(self, title: str):
        """Print a formatted section header."""
        print(f"\n{COLORS['BOLD']}{COLORS['BLUE']}{'=' * 80}{COLORS['RESET']}")
        print(f"{COLORS['BOLD']}{COLORS['BLUE']}  {title}{COLORS['RESET']}")
        print(f"{COLORS['BOLD']}{COLORS['BLUE']}{'=' * 80}{COLORS['RESET']}\n")
        
    def check_service(self, name: str, url: str, timeout: int = 2) -> bool:
        """Check if a service is running."""
        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code < 500
        except:
            return False
            
    def check_services(self) -> bool:
        """Check all required services."""
        self.print_header("🔍 Checking Service Health")
        
        services = [
            ("Ollama", "http://localhost:11434/api/version"),
            ("Qdrant", "http://localhost:6333/health"),
            ("Redis", "http://localhost:6379"),  # Will fail but that's ok
            ("Prometheus", "http://localhost:9090/-/healthy"),
            ("Grafana", "http://localhost:3000/api/health"),
            ("API", "http://localhost:8000/health")
        ]
        
        all_ok = True
        required_services = ["Ollama", "Qdrant", "Prometheus"]
        
        for name, url in services:
            status = self.check_service(name, url)
            
            if status:
                print(f"Checking {name}... {COLORS['GREEN']}✓ Running{COLORS['RESET']}")
            else:
                if name in required_services:
                    print(f"Checking {name}... {COLORS['RED']}✗ Not running{COLORS['RESET']}")
                    all_ok = False
                else:
                    print(f"Checking {name}... {COLORS['YELLOW']}⚠ Not running (optional){COLORS['RESET']}")
                    
        # Special check for Redis using redis-cli or network
        redis_ok = False
        try:
            result = subprocess.run(['redis-cli', 'ping'], capture_output=True, text=True)
            if result.stdout.strip() == 'PONG':
                print(f"Checking Redis... {COLORS['GREEN']}✓ Running{COLORS['RESET']}")
                redis_ok = True
        except FileNotFoundError:
            # Try network check as fallback
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', 6379))
                sock.close()
                if result == 0:
                    print(f"Checking Redis... {COLORS['GREEN']}✓ Running (port 6379 open){COLORS['RESET']}")
                    redis_ok = True
                else:
                    print(f"Checking Redis... {COLORS['RED']}✗ Not running{COLORS['RESET']}")
            except:
                print(f"Checking Redis... {COLORS['YELLOW']}⚠ Could not verify{COLORS['RESET']}")
        
        if not redis_ok and "Redis" in required_services:
            all_ok = False
            
        if not all_ok:
            print(f"\n{COLORS['RED']}Some required services are not running!{COLORS['RESET']}")
            print("Please start Docker Compose services:")
            print("  docker-compose up -d")
            return False
            
        print(f"\n{COLORS['GREEN']}All required services are healthy!{COLORS['RESET']}")
        return True
        
    def run_test_suite(self, suite_name: str, suite_path: str, args: argparse.Namespace) -> bool:
        """Run a specific test suite."""
        self.print_header(f"🧪 Running {suite_name.capitalize()} Tests")
        
        pytest_args = ['python', '-m', 'pytest', suite_path]
        
        # Add pytest arguments
        if args.verbose:
            pytest_args.append('-v')
        else:
            pytest_args.append('-q')
            
        if args.coverage:
            pytest_args.extend(['--cov=src', '--cov-report=term-missing'])
            
        if args.parallel and suite_name != 'infrastructure':
            pytest_args.extend(['-n', 'auto'])
            
        if args.html:
            Path('test-reports').mkdir(exist_ok=True)
            pytest_args.extend([
                f'--html=test-reports/{suite_name}-report.html',
                '--self-contained-html'
            ])
            
        # Add output capture
        pytest_args.extend(['--tb=short', '-r', 'fEsxXfE'])
        
        # Run tests
        result = subprocess.run(pytest_args, capture_output=True, text=True)
        
        # Parse results
        output = result.stdout + result.stderr
        
        # Extract test counts from pytest output
        import re
        
        # Look for test summary
        summary_match = re.search(r'(\d+) passed', output)
        if summary_match:
            self.results['passed'] += int(summary_match.group(1))
            
        failed_match = re.search(r'(\d+) failed', output)
        if failed_match:
            self.results['failed'] += int(failed_match.group(1))
            
        skipped_match = re.search(r'(\d+) skipped', output)
        if skipped_match:
            self.results['skipped'] += int(skipped_match.group(1))
            
        # Show results
        if result.returncode == 0:
            print(f"{COLORS['GREEN']}✓ All {suite_name} tests passed!{COLORS['RESET']}")
        else:
            print(f"{COLORS['RED']}✗ Some {suite_name} tests failed{COLORS['RESET']}")
            # Show failed test names
            failed_tests = re.findall(r'FAILED (.*?) -', output)
            for test in failed_tests[:10]:  # Show first 10 failures
                print(f"  - {test}")
                
        return result.returncode == 0
        
    def print_summary(self):
        """Print final test summary."""
        self.print_header("📊 Test Summary")
        
        self.results['total'] = self.results['passed'] + self.results['failed']
        
        print(f"{COLORS['BOLD']}Total Tests:{COLORS['RESET']} {self.results['total']}")
        print(f"{COLORS['GREEN']}Passed:{COLORS['RESET']} {self.results['passed']}")
        print(f"{COLORS['RED']}Failed:{COLORS['RESET']} {self.results['failed']}")
        
        if self.results['skipped'] > 0:
            print(f"{COLORS['YELLOW']}Skipped:{COLORS['RESET']} {self.results['skipped']}")
            
        if self.results['total'] > 0:
            success_rate = (self.results['passed'] * 100) // self.results['total']
            print(f"\n{COLORS['BOLD']}Success Rate:{COLORS['RESET']} {success_rate}%")
            
            if success_rate >= 90:
                print(f"{COLORS['GREEN']}✅ Excellent test coverage!{COLORS['RESET']}")
            elif success_rate >= 70:
                print(f"{COLORS['YELLOW']}⚠️  Good test coverage, but could be improved{COLORS['RESET']}")
            else:
                print(f"{COLORS['RED']}❌ Poor test coverage, needs attention{COLORS['RESET']}")
                
    def run(self, args: argparse.Namespace) -> int:
        """Main test execution."""
        print(f"{COLORS['BOLD']}{COLORS['BLUE']}🚀 LightRAG Backend Test Runner{COLORS['RESET']}")
        print(f"{COLORS['BLUE']}{'=' * 32}{COLORS['RESET']}\n")
        
        # Check if in virtual environment
        if not sys.prefix != sys.base_prefix:
            print(f"{COLORS['YELLOW']}Warning: Not in a virtual environment{COLORS['RESET']}")
            print("Consider activating your virtual environment first\n")
            
        # Check services
        if not self.check_services():
            return 1
            
        # Install test dependencies if needed
        try:
            import pytest
        except ImportError:
            print(f"\n{COLORS['YELLOW']}Installing test dependencies...{COLORS['RESET']}")
            subprocess.run([
                sys.executable, '-m', 'pip', 'install',
                'pytest', 'pytest-asyncio', 'pytest-cov', 'pytest-xdist', 'pytest-html'
            ])
            
        # Determine which suites to run
        suites_to_run = []
        if args.all or (not args.unit and not args.integration and not args.infrastructure):
            suites_to_run = list(self.test_suites.keys())
        else:
            if args.unit:
                suites_to_run.append('unit')
            if args.integration:
                suites_to_run.append('integration')
            if args.infrastructure:
                suites_to_run.append('infrastructure')
                
        # Run selected test suites
        overall_success = True
        for suite in suites_to_run:
            success = self.run_test_suite(suite, self.test_suites[suite], args)
            if not success:
                overall_success = False
                
        # Print summary
        self.print_summary()
        
        # Additional info
        if args.coverage:
            print(f"\n{COLORS['BOLD']}Coverage Report:{COLORS['RESET']}")
            print("Terminal report shown above")
            print("HTML report: htmlcov/index.html")
            
        if args.html:
            print(f"\n{COLORS['BOLD']}HTML Test Reports:{COLORS['RESET']}")
            print("Reports saved in: test-reports/")
            
        return 0 if overall_success else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='LightRAG Backend Test Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --unit            # Run only unit tests
  python run_tests.py -v --coverage     # Verbose with coverage
  python run_tests.py --parallel        # Run tests in parallel
        """
    )
    
    # Test selection arguments
    parser.add_argument('--all', action='store_true',
                       help='Run all test suites (default)')
    parser.add_argument('--unit', action='store_true',
                       help='Run unit tests')
    parser.add_argument('--integration', action='store_true',
                       help='Run integration tests')
    parser.add_argument('--infrastructure', action='store_true',
                       help='Run infrastructure tests')
    
    # Test execution options
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose test output')
    parser.add_argument('-c', '--coverage', action='store_true',
                       help='Generate coverage report')
    parser.add_argument('-p', '--parallel', action='store_true',
                       help='Run tests in parallel (not for infrastructure tests)')
    parser.add_argument('--html', action='store_true',
                       help='Generate HTML test reports')
    
    args = parser.parse_args()
    
    # Run tests
    runner = TestRunner()
    return runner.run(args)


if __name__ == '__main__':
    sys.exit(main())