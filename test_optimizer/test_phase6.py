"""
Test script for Phase 6: Smart Execution Ordering
"""

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from data.data_loader import DataLoader
from execution.dependency_analyzer import DependencyAnalyzer
from execution.priority_calculator import PriorityCalculator
from execution.execution_scheduler import ExecutionScheduler
from execution.execution_plan import ExecutionPlanGenerator


def main():
    """Test Phase 6 implementation."""
    # Paths to data directories
    project_root = Path(__file__).parent.parent
    test_cases_dir = project_root / "json-data" / "test_cases"
    steps_dir = project_root / "json-data" / "steps_in_test_cases"
    
    print("=" * 80)
    print("PHASE 6 TEST: Smart Execution Ordering")
    print("=" * 80)
    print()
    
    # Load test cases
    print("1. Loading test cases...")
    loader = DataLoader(str(test_cases_dir), str(steps_dir))
    test_cases = loader.load_all()
    print(f"   Loaded {len(test_cases)} test cases")
    print()
    
    # Test Dependency Analyzer
    print("2. Testing Dependency Analyzer...")
    dependency_analyzer = DependencyAnalyzer()
    dependency_analysis = dependency_analyzer.analyze_dependencies(test_cases)
    
    print(f"   Test cases with dependencies: {dependency_analysis['summary']['test_cases_with_dependencies']}")
    print(f"   Total dependencies: {dependency_analysis['summary']['total_dependencies']}")
    print(f"   Circular dependencies: {dependency_analysis['summary']['circular_dependency_count']}")
    
    if dependency_analysis['circular_dependencies']:
        print(f"   ⚠️  Warning: {len(dependency_analysis['circular_dependencies'])} circular dependencies found")
    else:
        print(f"   ✓ No circular dependencies")
    
    # Get execution order from dependencies
    dep_order = dependency_analyzer.get_execution_order(dependency_analysis['dependencies'])
    print(f"   Dependency-based order: {len(dep_order)} test cases")
    print()
    
    # Test Priority Calculator
    print("3. Testing Priority Calculator...")
    priority_calculator = PriorityCalculator()
    priorities = priority_calculator.calculate_priorities(test_cases)
    priority_categories = priority_calculator.categorize_priorities(priorities)
    
    print(f"   Priority scores calculated for {len(priorities)} test cases")
    print(f"   Smoke tests (80-100): {len(priority_categories['smoke'])}")
    print(f"   High priority (60-79): {len(priority_categories['high'])}")
    print(f"   Medium priority (40-59): {len(priority_categories['medium'])}")
    print(f"   Low priority (0-39): {len(priority_categories['low'])}")
    
    # Show top priority test cases
    sorted_priorities = sorted(priorities.items(), key=lambda x: x[1], reverse=True)
    print(f"   Top 5 priority test cases:")
    for test_id, score in sorted_priorities[:5]:
        print(f"     Test Case {test_id}: {score:.1f}")
    print()
    
    # Test Execution Scheduler
    print("4. Testing Execution Scheduler...")
    execution_scheduler = ExecutionScheduler()
    schedule = execution_scheduler.schedule_execution(test_cases)
    
    print(f"   Execution order generated: {len(schedule['execution_order'])} test cases")
    print(f"   Parallel groups identified: {len(schedule['parallel_groups'])}")
    print(f"   Estimated total time: {schedule['estimated_times']['total_time_minutes']:.1f} minutes")
    
    # Show first 10 in execution order
    print(f"   First 10 test cases in execution order:")
    for i, test_id in enumerate(schedule['execution_order'][:10], 1):
        priority = schedule['priorities'].get(test_id, 0)
        print(f"     {i:2d}. Test Case {test_id:3d} (Priority: {priority:.1f})")
    print()
    
    # Test Execution Plan Generator
    print("5. Testing Execution Plan Generator...")
    plan_generator = ExecutionPlanGenerator()
    execution_plan = plan_generator.generate_execution_plan(test_cases)
    
    print(f"   Execution plan generated successfully")
    print(f"   Summary:")
    summary = execution_plan['summary']
    print(f"     Total test cases: {summary['total_test_cases']}")
    print(f"     Estimated time: {summary['total_execution_time_minutes']:.1f} minutes")
    print(f"     Smoke tests: {summary['smoke_tests']}")
    print(f"     High priority: {summary['high_priority_tests']}")
    print(f"     Medium priority: {summary['medium_priority_tests']}")
    print(f"     Low priority: {summary['low_priority_tests']}")
    print(f"     Parallel groups: {summary['parallel_groups_count']}")
    print(f"     Checkpoints: {len(execution_plan['checkpoints'])}")
    print(f"     Rollback points: {len(execution_plan['rollback_points'])}")
    print()
    
    # Generate human-readable plan
    human_plan = plan_generator.generate_human_readable_plan(execution_plan)
    print("6. Human-Readable Execution Plan Preview:")
    print("-" * 80)
    print(human_plan[:600] + "..." if len(human_plan) > 600 else human_plan)
    print()
    
    print("=" * 80)
    print("PHASE 6 TEST COMPLETED")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  - {len(test_cases)} test cases analyzed")
    print(f"  - {dependency_analysis['summary']['total_dependencies']} dependencies identified")
    print(f"  - {len(priority_categories['smoke'])} smoke tests identified")
    print(f"  - Execution order: {len(schedule['execution_order'])} test cases")
    print(f"  - Estimated execution time: {schedule['estimated_times']['total_time_minutes']:.1f} minutes")
    print(f"  - {len(schedule['parallel_groups'])} parallel execution groups")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


