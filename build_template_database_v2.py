#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Template Database Builder v2 - Improved with incremental saves

Runs v0.92 on 400 training tasks to extract templates for v0.95.

Improvements over v1:
1. Incremental saves every 50 tasks (prevents data loss)
2. Resume capability (skip already processed tasks)
3. Faster execution (reduced cycles per task)
4. Better error handling

Expected duration: ~45-60 minutes for 400 tasks
"""

import json
import os
import time
from pathlib import Path
from prometheus_arc_v092_baseline import PrometheusARC_v092_Baseline
from arc_template_learner import TemplateLearner
from arc_program import ARCProgram


def load_all_training_tasks():
    """Load all training task IDs."""
    training_dir = Path('arc_agi_2/data/training')
    task_files = sorted(training_dir.glob('*.json'))
    return [f.stem for f in task_files]


def load_progress(progress_file):
    """Load progress from previous run."""
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            return json.load(f)
    return {'completed_tasks': [], 'results': []}


def save_progress(progress_file, progress_data):
    """Save progress incrementally."""
    with open(progress_file, 'w') as f:
        json.dump(progress_data, f, indent=2)


def run_v092_on_training_set(
    max_tasks=400,
    fitness_threshold=0.3,
    save_interval=50,
    max_cycles=2  # Reduced from 3 for speed
):
    """
    Run v0.92 on training tasks and extract templates.

    Args:
        max_tasks: Maximum number of tasks to process
        fitness_threshold: Minimum fitness to include in templates
        save_interval: Save progress every N tasks
        max_cycles: Max refinement cycles per task (reduced for speed)

    Returns:
        List of (task_id, pattern, fitness) tuples
    """
    print("=" * 80)
    print("🚀 Template Database Builder v2 (Incremental)")
    print("=" * 80)
    print()

    # Load task IDs
    task_ids = load_all_training_tasks()[:max_tasks]
    print(f"📝 Found {len(task_ids)} training tasks")
    print()

    # Load progress
    progress_file = 'arc_v092_training_progress.json'
    progress_data = load_progress(progress_file)
    completed_tasks = set(progress_data['completed_tasks'])
    results = progress_data['results']

    if completed_tasks:
        print(f"📂 Resuming from previous run ({len(completed_tasks)} tasks completed)")
        print()

    # Initialize solver (reduced cycles for speed)
    print("✅ Initializing v0.92 solver...")
    solver = PrometheusARC_v092_Baseline(
        use_llm=True,
        use_adaptive=True,
        use_metarefine=True,
        max_refinement_cycles=max_cycles  # Reduced from 3 to 2
    )
    print(f"   Max refinement cycles per task: {max_cycles} (faster mode)")
    print()

    # Process tasks
    start_time = time.time()

    for i, task_id in enumerate(task_ids, 1):
        # Skip if already processed
        if task_id in completed_tasks:
            continue

        try:
            # Load task
            task_file = f'arc_agi_2/data/training/{task_id}.json'
            with open(task_file, 'r') as f:
                task_data = json.load(f)

            train_examples = task_data['train']
            test_examples = task_data['test']

            # Solve
            result = solver.solve_task(train_examples, test_examples, task_id)

            fitness = result.get('fitness', 0.0)
            pattern = result.get('pattern', [])

            # Store if above threshold
            if fitness >= fitness_threshold:
                results.append({
                    'task_id': task_id,
                    'pattern': pattern,
                    'fitness': float(fitness)
                })
                status = "✓"
            else:
                status = "✗"

            # Update progress
            completed_tasks.add(task_id)
            progress_data['completed_tasks'] = list(completed_tasks)
            progress_data['results'] = results

            # Progress report
            elapsed = time.time() - start_time
            tasks_done = len(completed_tasks)
            avg_time = elapsed / tasks_done if tasks_done > 0 else 0
            eta_min = (len(task_ids) - tasks_done) * avg_time / 60

            success_count = len([r for r in results if r['fitness'] >= fitness_threshold])
            success_rate = success_count / tasks_done * 100 if tasks_done > 0 else 0

            print(f"[{tasks_done}/{len(task_ids)}] {status} {task_id}: {fitness:.3f} {pattern}")
            print(f"  Progress: {tasks_done/len(task_ids)*100:.1f}% | Success: {success_count}/{tasks_done} ({success_rate:.1f}%) | ETA: {eta_min:.1f}min")
            print()

            # Incremental save
            if tasks_done % save_interval == 0:
                save_progress(progress_file, progress_data)
                print(f"💾 Progress saved ({tasks_done} tasks completed)")
                print()

        except Exception as e:
            print(f"❌ Error processing {task_id}: {str(e)}")
            print()
            continue

    # Final save
    save_progress(progress_file, progress_data)

    print()
    print("=" * 80)
    print("✅ Template extraction complete!")
    print("=" * 80)
    print(f"Tasks processed: {len(completed_tasks)}")
    print(f"High-fitness results: {len(results)} (fitness ≥ {fitness_threshold})")
    print(f"Total time: {(time.time() - start_time)/60:.1f} minutes")
    print()

    return results


def build_template_database():
    """Build template database from training results."""
    print()
    print("=" * 80)
    print("🏗️  Building Template Database")
    print("=" * 80)
    print()

    # Step 1: Run v0.92 on training tasks
    print("Step 1: Running v0.92 on training tasks...")
    print("(Saves progress every 50 tasks)")
    print()

    results = run_v092_on_training_set(
        max_tasks=400,
        fitness_threshold=0.3,
        save_interval=50,
        max_cycles=2  # Faster mode
    )

    # Step 2: Extract templates
    print("Step 2: Extracting templates from results...")

    template_learner = TemplateLearner()

    for result in results:
        task_id = result['task_id']
        pattern = result['pattern']
        fitness = result['fitness']

        # Convert pattern to ARCProgram
        operations = [(op_name, {}) for op_name in pattern]
        program = ARCProgram(operations)

        # Record success
        template_learner.record_success(program, task_id, fitness)

    print(f"   Recorded {len(results)} successful programs")
    print()

    # Step 3: Save template database
    output_file = 'arc_v095_training_400_templates.json'
    template_learner.save_database(output_file)

    # Get statistics
    db = template_learner.get_database()
    num_programs = len(db['programs'])
    num_templates = len(db['templates'])

    print(f"✅ Template database saved: {output_file}")
    print(f"   Programs: {num_programs}")
    print(f"   Templates: {num_templates}")
    print()

    # Show top templates
    if num_templates > 0:
        print("Top 10 Templates:")
        templates = db['templates']

        # Sort by usage count
        template_list = [
            (pattern, stats['count'], stats['avg_fitness'])
            for pattern, stats in templates.items()
        ]
        template_list.sort(key=lambda x: x[1], reverse=True)

        for i, (pattern, count, avg_fitness) in enumerate(template_list[:10], 1):
            print(f"  {i}. {pattern}: {count} uses, {avg_fitness:.3f} avg fitness")

    print()
    print("=" * 80)
    print("🎉 Template database build complete!")
    print("=" * 80)
    print()


if __name__ == '__main__':
    build_template_database()
