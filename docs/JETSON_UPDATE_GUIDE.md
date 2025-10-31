# Jetson Update Guide: Reconcile Existing Repository

This guide helps you update your existing Prometheus repository on Jetson to the latest v0.19 branch with v0.65-v0.68 implementation.

---

## Step 1: Diagnose Current State

Run these commands on your Jetson to understand what you have:

```bash
cd /path/to/your/existing/Prometheus_v0_PoC

# Check current branch
git branch
# Note: You might be on 'master', 'v0.19', or another branch

# Check latest commits
git log --oneline -5
# Note: If you don't see commit 905a7e4, you're behind

# Check for local changes
git status
# Note: See if you have uncommitted work

# Verify remote
git remote -v
# Should show: https://github.com/pmcray/Prometheus_v0_PoC.git
```

---

## Step 2: Choose Your Reconciliation Strategy

### Option A: You Have NO Local Changes (Safest)

If `git status` shows "working tree clean":

```bash
# Fetch latest from GitHub
git fetch origin

# Switch to v0.19 branch
git checkout v0.19

# If it says "branch v0.19 not found locally", create it tracking remote:
git checkout -b v0.19 origin/v0.19

# Verify you have the latest
git log --oneline -1
# Should show: 2dff469 Add Jetson Orin Nano setup guide...
```

---

### Option B: You Have Local Changes to Keep

If `git status` shows uncommitted changes you want to keep:

```bash
# Save your local changes
git stash save "My local work before updating to v0.19"

# Fetch latest from GitHub
git fetch origin

# Switch to v0.19
git checkout v0.19

# Apply your saved changes back
git stash pop

# Resolve any conflicts if they occur
# Then commit your merged work
git add .
git commit -m "Merged local changes with v0.19"
```

---

### Option C: Start Fresh (Most Reliable)

If you want a clean slate or have complex local changes:

```bash
# Backup your existing work
cd /path/to/your/existing/Prometheus_v0_PoC
cd ..
mv Prometheus_v0_PoC Prometheus_v0_PoC.backup_$(date +%Y%m%d)

# Clone fresh from GitHub
git clone https://github.com/pmcray/Prometheus_v0_PoC.git
cd Prometheus_v0_PoC

# Checkout v0.19 branch
git checkout v0.19

# Verify
git log --oneline -5
```

Expected output:
```
2dff469 Add Jetson Orin Nano setup guide and GitHub push instructions
905a7e4 Implement Prometheus v0.65-v0.68: Generalized Capability Acquisition
816fb4b Latest version of workplan for v0.40-v0.44
...
```

---

### Option D: You're on an Old Branch (e.g., master)

If you're on `master` or an old version branch:

```bash
# See what branches exist
git branch -a

# Fetch all updates
git fetch origin

# List available branches after fetch
git branch -a
# You should see: remotes/origin/v0.19

# Switch to v0.19 (creates local tracking branch)
git checkout -b v0.19 origin/v0.19

# Verify
git log --oneline -1
# Should show: 2dff469
```

---

## Step 3: Verify Update Success

After updating, verify you have all new files:

```bash
# Check for new v0.65-v0.68 files
ls -lh benchmarks/prometheus_bench_v0_2.py
ls -lh benchmarks/baseline_agents.py
ls -lh prometheus/domain_expert_agent.py
ls -lh prometheus/generalist_planner.py
ls -lh prometheus/iee.py

# Check for setup guides
ls -lh JETSON_SETUP_GUIDE.md
ls -lh V0_65_TO_V0_74_IMPLEMENTATION_SUMMARY.md

# All should exist (not "No such file")
```

### Run Verification Tests

```bash
# Activate your venv if you have one
source venv_jetson/bin/activate  # or create new venv

# Install/update dependencies
pip install -r requirements.txt
pip install pytest

# Run v0.65-v0.68 tests
python3 verify_v0_65.py
python3 test_iee_v0_66_direct.py
python3 test_domain_expert_standalone.py
python3 test_generalist_planner_standalone.py
```

Expected: All tests pass (29/29)

---

## Step 4: Merge Local Work (if needed)

If you had local work in the backup and want to merge it:

```bash
# Compare what's different
diff -r Prometheus_v0_PoC.backup_YYYYMMDD/ Prometheus_v0_PoC/ \
    --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
    > differences.txt

# Review differences
less differences.txt

# Manually copy any custom files you want to keep
cp Prometheus_v0_PoC.backup_YYYYMMDD/path/to/your/file.py Prometheus_v0_PoC/

# Or use a merge tool
meld Prometheus_v0_PoC.backup_YYYYMMDD/ Prometheus_v0_PoC/
```

---

## Step 5: Set Up for Development

Once updated, set up your Jetson environment:

```bash
cd ~/path/to/Prometheus_v0_PoC

# Follow the setup guide
cat JETSON_SETUP_GUIDE.md

# Quick setup
python3 -m venv venv_jetson
source venv_jetson/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install PyTorch for Jetson (see JETSON_SETUP_GUIDE.md for details)
pip install torch torchvision torchaudio
```

---

## Common Issues & Solutions

### Issue 1: "Your branch is behind 'origin/v0.19'"

```bash
# Simply pull the latest
git pull origin v0.19
```

### Issue 2: "error: Your local changes would be overwritten"

```bash
# Stash your changes first
git stash save "Temporary save before update"
git pull origin v0.19
git stash pop  # Apply changes back
```

### Issue 3: "fatal: refusing to merge unrelated histories"

This happens if your local repo is completely different. Use Option C (Start Fresh).

### Issue 4: "Branch v0.19 not found"

```bash
# Fetch updates first
git fetch origin

# Then checkout
git checkout -b v0.19 origin/v0.19
```

### Issue 5: Conflicts after merge

```bash
# List conflicted files
git status | grep "both modified"

# Edit each conflicted file, resolve conflicts marked by:
# <<<<<<< HEAD
# your changes
# =======
# incoming changes
# >>>>>>> origin/v0.19

# After resolving, mark as resolved
git add resolved_file.py

# Complete the merge
git commit -m "Resolved merge conflicts"
```

---

## Quick Reference: Update Commands

**For clean working tree:**
```bash
git fetch origin
git checkout v0.19
git pull origin v0.19
```

**For uncommitted changes:**
```bash
git stash
git fetch origin
git checkout v0.19
git pull origin v0.19
git stash pop
```

**For fresh start:**
```bash
cd ..
mv Prometheus_v0_PoC Prometheus_v0_PoC.backup
git clone https://github.com/pmcray/Prometheus_v0_PoC.git
cd Prometheus_v0_PoC
git checkout v0.19
```

---

## What You Should Have After Update

### New Files (v0.65-v0.68):
- ✅ `benchmarks/prometheus_bench_v0_2.py` (719 lines)
- ✅ `benchmarks/baseline_agents.py` (215 lines)
- ✅ `prometheus/domain_expert_agent.py` (462 lines)
- ✅ `prometheus/generalist_planner.py` (409 lines)
- ✅ `prometheus/iee.py` (enhanced)

### Test Files:
- ✅ `verify_v0_65.py`
- ✅ `test_iee_v0_66_direct.py`
- ✅ `test_domain_expert_standalone.py`
- ✅ `test_generalist_planner_standalone.py`

### Documentation:
- ✅ `JETSON_SETUP_GUIDE.md`
- ✅ `V0_65_TO_V0_74_IMPLEMENTATION_SUMMARY.md`
- ✅ `CLAUDE.md`
- ✅ `PUSH_TO_GITHUB.md`
- ✅ `Project Prometheus_ Detailed Work Plans for Demonstrator v0.65-v0.74.md`

### Updated Files:
- ✅ `.gitignore` (excludes venv, models, etc.)

---

## Verification Checklist

After updating, verify:

- [ ] On branch v0.19: `git branch` shows `* v0.19`
- [ ] Latest commit: `git log -1` shows commit 2dff469 or 905a7e4
- [ ] New files exist: `ls benchmarks/prometheus_bench_v0_2.py`
- [ ] Tests pass: All 29/29 tests passing
- [ ] Setup guide present: `cat JETSON_SETUP_GUIDE.md` works
- [ ] No uncommitted changes: `git status` shows clean tree (unless you added new work)

---

## After Successful Update

Once updated, you're ready to:

1. **Follow JETSON_SETUP_GUIDE.md** to install dependencies
2. **Download models** (DeepSeek-Coder, Llama 3.1, Stable Diffusion)
3. **Start v0.69 development** with real GPU acceleration
4. **Run evolutionary loops** with local LLMs

---

## Need Help?

If you encounter issues not covered here:

1. Check git status: `git status`
2. Check remote: `git remote -v`
3. Check logs: `git log --graph --oneline --all -10`
4. Check branches: `git branch -a`

Then share the output and I can help troubleshoot!

---

*Ready to update and continue development on Jetson!*