# IOI Synthesizer Improvements v0.76

**Date:** October 10, 2025
**Status:** Prompt improvements complete, local model CUDA issue identified

---

## Summary

Significantly improved the IOI Bronze synthesizer with better prompt engineering, few-shot examples, and clearer instructions. Both cloud (`ioi_synthesizer.py`) and local (`ioi_synthesizer_local.py`) versions updated.

---

## Improvements Made

### 1. Enhanced Synthesis Prompts

**Before:**
- Basic instructions without examples
- Generic "use suggested algorithms" guidance
- Minimal formatting requirements

**After:**
- **Few-shot examples** showing 3 solved USACO Bronze problems
  - Count Even Numbers (simple iteration)
  - Find Maximum (built-in functions)
  - Sum of Array (aggregation)
- **Critical requirements** section with 9 specific guidelines
- **Common patterns** section with Bronze-level idioms
- **Clearer output format** with emphasis on exact matching

### 2. Improved Classification Prompts

**Before:**
- Simple list of available primitives
- No examples of classifications
- Generic JSON schema

**After:**
- **Classification examples** showing 3 problem → algorithm mappings
- **Categorized primitives** with emoji icons for clarity
- **Specific guidance** on choosing 3-5 most relevant algorithms
- **Bronze-level emphasis** preferring simpler approaches

### 3. Key Enhancements

#### Synthesis Prompt Improvements:
```python
few_shot_examples = """
EXAMPLE 1 - Count Even Numbers:
Problem: Count how many even numbers are in an array.
Input format: First line N, second line N integers
Output: Single integer

Solution:
```python
n = int(input())
arr = list(map(int, input().split()))
count = sum(1 for x in arr if x % 2 == 0)
print(count)
```
...
```

#### Critical Requirements Added:
1. Read input EXACTLY as specified
2. Output EXACTLY matches expected format
3. Use the suggested algorithms
4. Handle edge cases: empty arrays, single elements, all same values
5. Ensure O(n) or better complexity
6. Production-quality code
7. NO debugging print statements
8. NO test cases in output
9. Complete and immediately executable

#### Common Patterns Section:
- Array input: `n = int(input()); arr = list(map(int, input().split()))`
- Single output: `print(result)`
- Multiple outputs: `print(' '.join(map(str, results)))`
- String processing: `s = input().strip()`
- Edge cases: always check empty/single element

### 4. Classification Improvements

**Added Few-Shot Examples:**
```
Example 1: "Count even numbers" → ["array", "math"] → ["use_array", "count_if"]
Example 2: "Max subarray sum" → ["array", "dp"] → ["use_array", "dp_max_subarray_sum"]
Example 3: "Sort and find median" → ["array", "sorting"] → ["use_array", "sort_ascending"]
```

**Organized Primitives with Categories:**
- 📦 Data Structures (9 primitives)
- 🔍 Search & Sort (5 primitives)
- 📊 Array Operations (8 primitives)
- 📝 String Operations (5 primitives)
- 🌐 Graph Algorithms (8 primitives)
- 💡 Dynamic Programming (6 primitives)
- 🎯 Greedy Algorithms (4 primitives)
- 🔢 Math (4 primitives)

---

## Files Modified

1. **`ioi_synthesizer.py`** (cloud version)
   - Updated `_build_synthesis_prompt()` method (lines 136-231)
   - Updated classification prompt (lines 330-406)
   - Added few-shot examples and critical requirements

2. **`ioi_synthesizer_local.py`** (local version)
   - Updated `_build_synthesis_prompt()` method (lines 239-341)
   - Updated `_build_classification_prompt()` method (lines 429-493)
   - Same improvements as cloud version

3. **`test_local_model.py`** (new file, 150 lines)
   - Integration test for local model
   - Tests classification + synthesis + testing pipeline
   - Validates on Count Even Numbers problem

---

## Expected Improvements

### Synthesis Quality:
- **Better input/output handling**: Few-shot examples show exact format
- **Correct algorithm usage**: Clear guidance on which primitives to use
- **Cleaner code**: No debugging output, production-quality standards
- **Edge case handling**: Explicit reminders for empty/single element cases

### Classification Accuracy:
- **More relevant algorithms**: Examples guide better primitive selection
- **Appropriate complexity**: Bronze-level emphasis on simple solutions
- **Better categorization**: Clear primary vs secondary categories

### Overall System:
- **Higher solve rate**: Target 40% → 50-60% on USACO Bronze problems
- **Fewer test failures**: Better output formatting reduces mismatches
- **Faster debugging**: Clear requirements help models understand expectations

---

## Installation Status

### ✅ Completed:
1. Synthesizer prompt improvements (both cloud and local)
2. llama.cpp build (100% complete)
3. llama-cli binary available (2.6MB)
4. DeepSeek-Coder-1.3B model downloaded (834MB)
5. Environment variables configured

### ⚠️  Issue Identified:
**CUDA PTX Toolchain Compatibility Problem**

**Error:**
```
ggml_cuda_compute_forward: MUL_MAT failed
CUDA error: the provided PTX was compiled with an unsupported toolchain.
```

**Root Cause:**
- llama.cpp built with CUDA 12.9 (nvcc)
- Jetson Orin Nano compute capability 8.7 (Ampere)
- PTX compiled for wrong architecture targets

**Current Build Settings:**
```cmake
CUDA architectures: 50-virtual;61-virtual;70-virtual;75-virtual;80-virtual;86-real;89-real
```

**Jetson Orin Nano Needs:**
```cmake
CUDA architectures: 87 (native compute capability 8.7)
```

---

## Next Steps

### Option A: Rebuild llama.cpp with Correct Architecture
```bash
cd ~/llama.cpp/build
cmake .. -DGGML_CUDA=ON -DLLAMA_CURL=OFF -DCMAKE_CUDA_ARCHITECTURES=87
cmake --build . --config Release -j4
```

**Pros:**
- Native GPU support (2-3 tokens/sec)
- Uses Jetson's 4GB GPU efficiently
- Best performance for local inference

**Cons:**
- 10-15 minute rebuild
- May hit same toolchain issue

### Option B: Use CPU-Only Mode
```bash
cd ~/llama.cpp/build
cmake .. -DGGML_CUDA=OFF -DLLAMA_CURL=OFF
cmake --build . --config Release -j4
```

**Pros:**
- No CUDA compatibility issues
- Guaranteed to work
- Still functional (slower)

**Cons:**
- Slower inference (0.5-1 tok/sec vs 2-3)
- Doesn't utilize GPU

### Option C: Test with Mock/Cloud Mode First
```bash
python3 benchmark_ioi_bronze.py --problems easy --mode mock
# OR with Gemini API:
export GOOGLE_API_KEY="your_key"
python3 benchmark_ioi_bronze.py --problems easy --mode cloud
```

**Pros:**
- Validates improved prompts immediately
- No waiting for CUDA fix
- Can benchmark all 30 problems

**Cons:**
- Requires API key for cloud mode
- Mock mode limited (33% on easy)

---

## Recommendation

**Proceed with Option C first**, then Option A:

1. **Immediate**: Test improved prompts with mock/cloud mode
   - Validate prompt improvements work
   - Benchmark on 30 USACO Bronze problems
   - Compare vs baseline (33% on easy 3 problems)

2. **Parallel**: Rebuild llama.cpp with correct architecture
   - Try `CMAKE_CUDA_ARCHITECTURES=87` first
   - Fall back to CPU-only if needed
   - Test once rebuild complete

3. **Final**: Compare all 3 modes (mock vs cloud vs local)
   - Document performance: accuracy, speed, cost
   - Choose best mode for production use

---

## Performance Predictions

### With Improved Prompts:

| Mode | Easy (9) | Medium (17) | Hard (4) | Overall (30) | Notes |
|------|----------|-------------|----------|--------------|-------|
| **Mock (old)** | 33% | 10% | 0% | 13% | Baseline |
| **Mock (new)** | 50-60% | 20-30% | 5-10% | 30-35% | Better prompts |
| **Cloud (new)** | 70-80% | 50-60% | 20-30% | 55-65% | Gemini 1.5 Flash |
| **Local (new)** | 60-70% | 40-50% | 15-25% | 45-55% | DeepSeek-Coder-1.3B |

**Target**: 40% overall → **Expected: 45-65%** depending on mode

---

## Technical Details

### Prompt Length:
- **Synthesis prompt**: ~1200 tokens (was ~500)
  - Added 3 few-shot examples (~300 tokens)
  - Added critical requirements (~200 tokens)
  - Added common patterns (~200 tokens)

- **Classification prompt**: ~800 tokens (was ~400)
  - Added 3 classification examples (~150 tokens)
  - Added organized primitive categories (~250 tokens)

### Token Efficiency:
- Longer prompts → better guidance → fewer retries
- Net effect: potentially faster despite longer prompts
- Quality > speed for Bronze-level problems

---

## Code Quality Improvements

### Input Handling:
```python
# Old (implicit):
n = int(input())
arr = list(map(int, input().split()))

# New (explicit guidance):
"Read input EXACTLY as specified in the problem format"
"Array input: n = int(input()); arr = list(map(int, input().split()))"
```

### Output Formatting:
```python
# Old (ambiguous):
print(result)

# New (explicit):
"Output EXACTLY matches expected format (no extra text, proper spacing)"
"Single output: print(result)"
"Multiple outputs: print(' '.join(map(str, results)))"
```

### Edge Cases:
```python
# Old (not mentioned):
# (models often forgot edge cases)

# New (explicit):
"Handle edge cases: empty arrays, single elements, all same values"
"Edge case: always check if array is empty or has 1 element"
```

---

## Validation Plan

### Test 1: Easy Problems (9 total)
- Count Even, Find Max, Sum Array
- Sort Array, Range Sum Query, Min/Max
- String Reverse, Count Vowels, Cumulative Sum, Filter Positive
- **Target**: 60% (5-6 solved)

### Test 2: Medium Problems (17 total)
- Count Occurrences, Reverse Array, Check Sorted, Count Unique
- Prefix Sum Query, GCD, Prime Check, Fibonacci
- Median, Mode, Second Max, Remove Duplicates
- Partition, Palindrome, Two Sum, Frequency Map
- **Target**: 50% (8-9 solved)

### Test 3: Hard Problems (4 total)
- Binary Search, Max Subarray Sum, LIS, Coin Change
- **Target**: 25% (1 solved)

### Overall:
- **Expected**: 14-16 / 30 (47-53%)
- **Target**: 12+ / 30 (40%+)

---

## Conclusions

✅ **Prompt improvements complete** (both cloud and local versions)
✅ **Installation 95% complete** (binary and model ready)
⚠️  **CUDA compatibility issue** (needs rebuild with arch=87)
⏳ **Testing pending** (can use mock/cloud while fixing CUDA)

**Next immediate action**: Test improved prompts with available modes, then fix CUDA issue for local model support.

---

*Generated: October 10, 2025*
*Prometheus v0.76: IOI Bronze Synthesizer Improvements*
*Status: Prompts complete, local model CUDA issue identified*
