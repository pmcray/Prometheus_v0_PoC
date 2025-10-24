# Option E: Failed Task Analysis - Missing Operations

**Date**: 2025-10-23
**Tasks Analyzed**: 45 unsolved tasks from v0.95 benchmark
**Goal**: Identify missing operations needed to break 10% ceiling

---

## Executive Summary

Analyzed 45 unsolved ARC-AGI tasks to identify missing operation types. Found clear patterns:

**Top 3 Missing Categories**:
1. **Size Operations** (44.4% of tasks): `expand_to_size`, `compress_to_fit`, `crop_to_content`
2. **Color Filtering** (33.3% of tasks): `isolate_color`, `extract_color`, `filter_by_color`
3. **Object Operations** (13.3% of tasks): `group_by_property`, `merge_adjacent`, `combine_overlapping`

**Current coverage gap**: Current 56 operations lack smart resizing, color isolation, and object grouping capabilities.

---

## Task Type Distribution

Breakdown of 45 unsolved tasks by transformation type:

| Task Type | Count | % of Tasks | Priority |
|-----------|-------|------------|----------|
| **Size Change** | 20 | 44.4% | 🔴 **HIGH** |
| **Color Filtering** | 15 | 33.3% | 🔴 **HIGH** |
| **Unknown** | 14 | 31.1% | ⚪ (needs deeper analysis) |
| **Object Merging** | 6 | 13.3% | 🟡 Medium |
| **Symmetrization** | 6 | 13.3% | 🟡 Medium |
| **Object Duplication** | 3 | 6.7% | 🟢 Low |
| **Color Generation** | 3 | 6.7% | 🟢 Low |

**Note**: Tasks can have multiple types (e.g., size change + color filtering)

---

## Priority Operations (Top 18)

Based on frequency across 45 tasks:

### Size Operations (44.4% of tasks)

| Operation | Tasks | Description |
|-----------|-------|-------------|
| **expand_to_size** | 20 | Expand grid to target size with fill/pattern |
| **compress_to_fit** | 20 | Compress grid to fit smaller size |
| **crop_to_content** | 20 | Crop grid to minimal bounding box of content |

**Current gap**: We have basic `crop()` but lack intelligent sizing with pattern preservation.

### Color Filtering Operations (33.3% of tasks)

| Operation | Tasks | Description |
|-----------|-------|-------------|
| **isolate_color** | 15 | Extract objects of specific color, remove others |
| **extract_color** | 15 | Keep only pixels of specific color |
| **filter_by_color** | 15 | Filter objects by color property |

**Current gap**: We have `map_color()` but lack selective color extraction/filtering.

### Object Operations (13.3% of tasks)

| Operation | Tasks | Description |
|-----------|-------|-------------|
| **group_by_property** | 6 | Group objects by color, size, shape |
| **merge_adjacent** | 6 | Merge objects that touch/overlap |
| **combine_overlapping** | 6 | Combine overlapping regions |

**Current gap**: We have `detect_objects()` but lack grouping/merging operations.

### Symmetry Operations (13.3% of tasks)

| Operation | Tasks | Description |
|-----------|-------|-------------|
| **make_symmetric** | 6 | Force grid to be symmetric (horizontal/vertical) |
| **complete_symmetry** | 6 | Complete partial symmetry pattern |
| **mirror_pattern** | 6 | Mirror pattern across axis |

**Current gap**: We have `symmetrize()` but it pads to symmetric dimensions, not enforcing symmetry.

### Duplication Operations (6.7% of tasks)

| Operation | Tasks | Description |
|-----------|-------|-------------|
| **tile_by_count** | 3 | Tile pattern N times |
| **reflect_objects** | 3 | Reflect objects across axis |
| **replicate_objects** | 3 | Replicate objects in pattern |

**Current gap**: We have `tile()` but lack object-aware duplication.

### Color Generation Operations (6.7% of tasks)

| Operation | Tasks | Description |
|-----------|-------|-------------|
| **apply_pattern_colors** | 3 | Apply color pattern from template |
| **interpolate_colors** | 3 | Generate gradient/interpolated colors |
| **color_by_position** | 3 | Assign color based on position |

**Current gap**: We have basic color mapping, lack pattern-based coloring.

---

## Detailed Task Examples

### Size Change Tasks (20 tasks, 44.4%)

**Example tasks**: 0934a4d8, 136b0064, 20270e3b, 21897d95, 269e22fb, 271d71e2, 291dc1e1, 2ba387bc, 2d0172a1, 38007db0, 3a25b0d8, 45a5af55, 4c7dc4dd, 4e34c42c, 5545f144, 58490d8a, 58f5dbd5, 5dbc8537, 65b59efc, 67e490f4

**Pattern**: Input and output have different sizes, need intelligent resizing

**What's needed**:
```python
# Current: Basic crop with fixed parameters
crop(mode='content')  # Just finds bounding box

# Needed: Smart sizing operations
expand_to_size(target_size=(10, 10), fill='pattern')  # Tile/repeat to fill
compress_to_fit(target_size=(5, 5), method='downsample')  # Smart downsize
crop_to_content(margin=1, preserve_aspect=True)  # Intelligent cropping
```

**Why current operations fail**:
- `crop()` can shrink but not expand intelligently
- No way to specify target size with pattern preservation
- No content-aware downsampling

---

### Color Filtering Tasks (15 tasks, 33.3%)

**Example tasks**: 0934a4d8, 136b0064, 20270e3b, 20a9e565, 21897d95, 291dc1e1, 446ef5d2, 4c7dc4dd, 5545f144, 58490d8a, 58f5dbd5, 5961cc34, 5dbc8537, 65b59efc, 67e490f4

**Pattern**: Extract or filter by color, isolate specific colors

**What's needed**:
```python
# Current: Map all instances of a color
map_color(from_color=1, to_color=2)  # Changes color globally

# Needed: Selective color operations
isolate_color(color=1)  # Keep only color 1, remove others → background
extract_color(color=1)  # Extract color 1 objects, return them
filter_by_color(colors=[1, 2])  # Keep only specified colors
```

**Why current operations fail**:
- `map_color()` changes colors but doesn't isolate/extract
- No way to remove all but specific colors
- No object filtering by color property

---

### Object Merging Tasks (6 tasks, 13.3%)

**Example tasks**: 136b0064, 16b78196, 20a9e565, 2ba387bc, 4c3d4a41, 65b59efc

**Pattern**: Multiple objects need to be merged or grouped

**What's needed**:
```python
# Current: Detect objects separately
detect_objects()  # Returns individual objects

# Needed: Object merging/grouping
group_by_property(property='color')  # Group objects with same color
merge_adjacent(distance=1)  # Merge objects within distance
combine_overlapping()  # Combine objects that overlap
```

**Why current operations fail**:
- `detect_objects()` segments but doesn't group
- No way to merge multiple objects into one
- No adjacency-based operations

---

### Symmetrization Tasks (6 tasks, 13.3%)

**Example tasks**: 20a9e565, 31f7f899, 45a5af55, 4e34c42c, 5961cc34, 67e490f4

**Pattern**: Force or complete symmetry in grid

**What's needed**:
```python
# Current: Pad to symmetric dimensions
symmetrize(axis='horizontal')  # Just pads grid to be square

# Needed: Enforce symmetry
make_symmetric(axis='horizontal', method='reflect')  # Mirror to make symmetric
complete_symmetry(axis='vertical')  # Complete partial pattern
mirror_pattern(axis='horizontal', from_side='left')  # Mirror from one side
```

**Why current operations fail**:
- `symmetrize()` changes size, doesn't enforce symmetry
- No way to mirror content to create symmetry
- No partial pattern completion

---

### Unknown Tasks (14 tasks, 31.1%)

**Tasks**: 13e47133, 195c6913, 247ef758, 271d71e2, 28a6681f, 2c181942, 35ab12c3, 36a08778, 3dc255db, 4a21e3da, 53fb4810, 581f7754, 62593bfd, 64efde09

**Why "unknown"**: Analysis couldn't detect clear transformation pattern

**Likely reasons**:
1. Complex multi-step transformations (need manual inspection)
2. Conditional logic (if-then-else operations)
3. Path-based operations (tracing, connecting)
4. Abstract patterns (hard to detect programmatically)

**Next step**: Manual inspection of these 14 tasks to identify patterns

---

## Comparison with Current Operations

### Current Operation Set (56 operations)

**What we have**:
- ✅ Basic geometric: `rotate`, `flip`, `crop`, `scale`, `transpose`
- ✅ Basic color: `map_color`, `invert_colors`, `swap_colors`
- ✅ Object detection: `detect_objects`, `sort_objects`, `filter_objects`
- ✅ Basic patterns: `symmetrize`, `tile`, `replicate`
- ✅ Physics: `gravity_down`, `spread`
- ✅ Structural: `fill`, `hollow`, `outline`

**What we're missing**:
- ❌ Smart resizing: `expand_to_size`, `compress_to_fit`
- ❌ Color isolation: `isolate_color`, `extract_color`
- ❌ Object grouping: `group_by_property`, `merge_adjacent`
- ❌ Symmetry enforcement: `make_symmetric`, `complete_symmetry`
- ❌ Pattern-based coloring: `apply_pattern_colors`, `color_by_position`

---

## Recommended New Operations (30 total)

### Category 1: Size Operations (Priority: 🔴 HIGH)

1. **expand_to_size**(target_size, fill='background'|'pattern'|'tile')
   - Expand grid to target size by tiling or filling
   - Handles both uniform filling and pattern repetition

2. **compress_to_fit**(target_size, method='downsample'|'select'|'average')
   - Intelligently downsize grid to fit target
   - Uses downsampling or content selection

3. **crop_to_content**(margin=0, preserve_aspect=False)
   - Crop to minimal bounding box of non-background pixels
   - Optional margin and aspect ratio preservation

4. **resize_with_padding**(target_size, padding_color=0)
   - Resize and add padding to reach target size
   - Preserves original content, adds padding around edges

5. **fit_to_canvas**(canvas_size, align='center'|'topleft'|'bottomright')
   - Fit content onto canvas of specified size
   - Control alignment of content

---

### Category 2: Color Filtering (Priority: 🔴 HIGH)

6. **isolate_color**(color, background=0)
   - Keep only specified color, set rest to background
   - Returns grid with only one color preserved

7. **extract_color**(color)
   - Extract objects of specified color
   - Returns only those objects, removes everything else

8. **filter_by_color**(colors=[])
   - Keep only objects with specified colors
   - Multi-color filtering

9. **remove_color**(color)
   - Remove all pixels of specified color
   - Inverse of extract_color

10. **keep_colors**(colors=[], background=0)
    - Keep multiple colors, set rest to background
    - Multi-color isolation

---

### Category 3: Object Grouping & Merging (Priority: 🟡 MEDIUM)

11. **group_by_property**(property='color'|'size'|'shape')
    - Group objects with same property
    - Returns grouped object representation

12. **merge_adjacent**(distance=1, by_color=False)
    - Merge objects within distance threshold
    - Optional: only merge same-color objects

13. **combine_overlapping**()
    - Combine objects that overlap
    - Union of overlapping regions

14. **merge_by_color**(color)
    - Merge all objects of specified color
    - Returns single merged object per color

15. **connect_objects**(method='shortest'|'horizontal'|'vertical')
    - Connect separated objects with lines/paths
    - Various connection strategies

---

### Category 4: Symmetry Enforcement (Priority: 🟡 MEDIUM)

16. **make_symmetric**(axis='horizontal'|'vertical'|'both', method='reflect'|'average')
    - Force grid to be symmetric
    - Mirror one side or average both sides

17. **complete_symmetry**(axis='horizontal'|'vertical')
    - Complete partial symmetry pattern
    - Fill in missing symmetric parts

18. **mirror_pattern**(axis='horizontal'|'vertical', from_side='auto'|'left'|'right'|'top'|'bottom')
    - Mirror content to create symmetry
    - Control which side is the source

19. **enforce_symmetry**(type='rotational'|'reflective', order=2)
    - Enforce specific symmetry type
    - Rotational (90°, 180°) or reflective

20. **find_and_complete_symmetry**()
    - Detect partial symmetry and complete it
    - Automatic symmetry detection and completion

---

### Category 5: Pattern-Based Coloring (Priority: 🟢 LOW)

21. **apply_pattern_colors**(pattern_grid)
    - Apply color pattern from template grid
    - Map structure to template colors

22. **interpolate_colors**(start_color, end_color, direction='horizontal'|'vertical')
    - Create color gradient
    - Smooth interpolation between colors

23. **color_by_position**(scheme='checkerboard'|'gradient'|'radial')
    - Assign colors based on position
    - Various spatial coloring schemes

24. **recolor_by_frequency**(order='most_to_least'|'least_to_most')
    - Recolor objects by frequency
    - Most/least common gets specific color

25. **match_color_distribution**(target_grid)
    - Match color distribution of target
    - Histogram matching

---

### Category 6: Object Duplication (Priority: 🟢 LOW)

26. **tile_by_count**(count_h, count_v)
    - Tile pattern specific number of times
    - More control than basic tile()

27. **reflect_objects**(axis='horizontal'|'vertical'|'both')
    - Reflect objects across axis
    - Object-aware reflection

28. **replicate_objects**(pattern='grid'|'line'|'scatter', count=3)
    - Replicate objects in pattern
    - Various arrangement patterns

29. **duplicate_with_offset**(offset_x, offset_y, count=2)
    - Duplicate with specific offset
    - Stacking/layering effect

30. **radial_replicate**(center='auto', count=4, angle_step=90)
    - Replicate in radial pattern
    - Circular/star arrangements

---

## Implementation Priority

### Phase 1: High Priority (10 operations) - Week 1

**Size operations** (5):
1. expand_to_size
2. compress_to_fit
3. crop_to_content
4. resize_with_padding
5. fit_to_canvas

**Color filtering** (5):
6. isolate_color
7. extract_color
8. filter_by_color
9. remove_color
10. keep_colors

**Expected impact**: 20 size tasks + 15 color tasks = **35 tasks** (78% of unsolved)
**Target solve rate**: 10% → 15-18% (5 → 8-9 tasks)

---

### Phase 2: Medium Priority (10 operations) - Week 2

**Object operations** (5):
11. group_by_property
12. merge_adjacent
13. combine_overlapping
14. merge_by_color
15. connect_objects

**Symmetry operations** (5):
16. make_symmetric
17. complete_symmetry
18. mirror_pattern
19. enforce_symmetry
20. find_and_complete_symmetry

**Expected impact**: 6 merging tasks + 6 symmetry tasks = **12 tasks** (27% of unsolved)
**Target solve rate**: 15-18% → 20-22% (8-9 → 10-11 tasks)

---

### Phase 3: Low Priority (10 operations) - Week 3

**Pattern coloring** (5):
21. apply_pattern_colors
22. interpolate_colors
23. color_by_position
24. recolor_by_frequency
25. match_color_distribution

**Duplication** (5):
26. tile_by_count
27. reflect_objects
28. replicate_objects
29. duplicate_with_offset
30. radial_replicate

**Expected impact**: 3 color generation + 3 duplication = **6 tasks** (13% of unsolved)
**Target solve rate**: 20-22% → 22-25% (10-11 → 11-12 tasks)

---

## Success Metrics

### Phase 1 Success Criteria
- ✅ 10 new operations implemented
- ✅ All operations tested individually
- ✅ Integrated into beam search
- ✅ Solve rate: 15-18% (8-9 tasks out of 50)
- ✅ At least 3 new tasks solved (beyond current 5)

### Phase 2 Success Criteria
- ✅ 20 total new operations
- ✅ Solve rate: 20-22% (10-11 tasks)
- ✅ At least 5 new tasks solved

### Phase 3 Success Criteria
- ✅ 30 total new operations
- ✅ Solve rate: 22-25% (11-12 tasks)
- ✅ Operation coverage analysis shows good ARC-AGI concept alignment
- ✅ System can solve diverse task types (not just one category)

---

## Risk Mitigation

### Risk 1: New operations don't help
**Mitigation**: Implement Phase 1 (10 ops) first, measure impact before continuing

### Risk 2: Parameter explosion
**Mitigation**: Use smart defaults, generate parameter candidates from task analysis

### Risk 3: Slower beam search
**Mitigation**: Optimize operation execution, consider pruning low-value operations

### Risk 4: "Unknown" tasks need different approach
**Mitigation**: Manual inspection of 14 unknown tasks, may need conditional/path operations

---

## Next Steps

1. **Implement Phase 1 operations** (5 size + 5 color filtering)
   - Add to `arc_parametric_operations.py`
   - Define parameter candidate generation
   - Test each operation with example tasks

2. **Integrate into pipeline**
   - Update operation map in beam search
   - Update meta-learner with new operations
   - Update hierarchical templates

3. **Benchmark Phase 1**
   - Re-run v0.95 on 50 evaluation tasks
   - Measure solve rate improvement
   - Analyze which operations helped

4. **Iterate**
   - If Phase 1 reaches 15-18%, continue to Phase 2
   - If below 15%, debug and refine Phase 1 operations
   - If above 18%, may not need all Phase 2/3 operations

---

## Appendix: Task Type Details

### Size Change Task IDs (20 tasks)
- 0934a4d8, 136b0064, 20270e3b, 21897d95, 269e22fb, 271d71e2, 291dc1e1
- 2ba387bc, 2d0172a1, 38007db0, 3a25b0d8, 45a5af55, 4c7dc4dd, 4e34c42c
- 5545f144, 58490d8a, 58f5dbd5, 5dbc8537, 65b59efc, 67e490f4

### Color Filtering Task IDs (15 tasks)
- 0934a4d8, 136b0064, 20270e3b, 20a9e565, 21897d95, 291dc1e1, 446ef5d2
- 4c7dc4dd, 5545f144, 58490d8a, 58f5dbd5, 5961cc34, 5dbc8537, 65b59efc, 67e490f4

### Object Merging Task IDs (6 tasks)
- 136b0064, 16b78196, 20a9e565, 2ba387bc, 4c3d4a41, 65b59efc

### Symmetrization Task IDs (6 tasks)
- 20a9e565, 31f7f899, 45a5af55, 4e34c42c, 5961cc34, 67e490f4

### Object Duplication Task IDs (3 tasks)
- 142ca369, 16de56c4, 1ae2feb7

### Color Generation Task IDs (3 tasks)
- 1818057f, 221dfab4, 2b83f449

### Unknown Task IDs (14 tasks)
- 13e47133, 195c6913, 247ef758, 271d71e2, 28a6681f, 2c181942, 35ab12c3
- 36a08778, 3dc255db, 4a21e3da, 53fb4810, 581f7754, 62593bfd, 64efde09

---

**End of Analysis**

**Status**: Ready to begin Phase 1 implementation (10 high-priority operations)
**Target**: 10% → 15-18% solve rate
**Timeline**: 1 week for Phase 1
