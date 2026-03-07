"""
WP70 Test Suite: Academic Paper & Reproducibility Package
==========================================================

TestPaperSection          Section dataclass
TestPaperOutline          Default outline, section count
TestReproducibilityScript Script generation
TestDependencyManifest    Capture, to_dict
TestCitationRecord        BibTeX format
TestContributionChecklist Items, completeness check
TestReproducibilityPackage Build, artefact files
TestWP70ExitCriteria      Six-criterion verifier
TestIntegration           End-to-end: package → artefacts
"""

import os
import pytest

from prometheus.wp70_paper_package import (
    CitationRecord,
    ContributionChecklist,
    DependencyManifest,
    PaperOutline,
    PaperSection,
    ReproducibilityPackage,
    ReproducibilityScript,
    verify_wp70_exit_criteria,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _package(tmp_path) -> ReproducibilityPackage:
    return ReproducibilityPackage(output_dir=str(tmp_path))


# ===========================================================================
# TestPaperSection
# ===========================================================================

class TestPaperSection:
    def test_fields(self):
        s = PaperSection(
            title="Introduction",
            number=1,
            content="This paper presents...",
            word_count_target=500,
        )
        assert s.title == "Introduction"
        assert s.number == 1

    def test_to_dict(self):
        s = PaperSection(title="Intro", number=1, content="...", word_count_target=500)
        d = s.to_dict()
        for k in ("title", "number", "content", "word_count_target"):
            assert k in d, f"Missing key: {k}"


# ===========================================================================
# TestPaperOutline
# ===========================================================================

class TestPaperOutline:
    def test_default_has_7_sections(self):
        outline = PaperOutline.default()
        assert len(outline.sections) == 7

    def test_section_titles_nonempty(self):
        outline = PaperOutline.default()
        for s in outline.sections:
            assert len(s.title) > 0

    def test_to_dict(self):
        outline = PaperOutline.default()
        d = outline.to_dict()
        assert "sections" in d
        assert "title" in d

    def test_has_introduction(self):
        outline = PaperOutline.default()
        titles = [s.title.lower() for s in outline.sections]
        assert any("introduction" in t for t in titles)

    def test_has_conclusion(self):
        outline = PaperOutline.default()
        titles = [s.title.lower() for s in outline.sections]
        assert any("conclusion" in t for t in titles)

    def test_has_safety_section(self):
        outline = PaperOutline.default()
        titles = [s.title.lower() for s in outline.sections]
        assert any("safety" in t or "alignment" in t for t in titles)

    def test_sections_numbered_sequentially(self):
        outline = PaperOutline.default()
        numbers = [s.number for s in outline.sections]
        assert numbers == list(range(1, len(numbers) + 1))


# ===========================================================================
# TestReproducibilityScript
# ===========================================================================

class TestReproducibilityScript:
    def test_generate_returns_string(self):
        script = ReproducibilityScript()
        code = script.generate()
        assert isinstance(code, str)
        assert len(code) > 0

    def test_script_is_valid_python(self):
        script = ReproducibilityScript()
        code = script.generate()
        # Should compile without error
        compile(code, "<string>", "exec")

    def test_script_contains_exit_criteria(self):
        script = ReproducibilityScript()
        code = script.generate()
        assert "verify_wp" in code or "exit_criteria" in code

    def test_script_saves_results(self):
        script = ReproducibilityScript()
        code = script.generate()
        assert "reproduce_results" in code or "json" in code

    def test_to_dict(self):
        script = ReproducibilityScript()
        d = script.to_dict()
        assert "code_length" in d or "description" in d or isinstance(d, dict)


# ===========================================================================
# TestDependencyManifest
# ===========================================================================

class TestDependencyManifest:
    def test_capture_returns_manifest(self):
        manifest = DependencyManifest.capture()
        assert isinstance(manifest, DependencyManifest)

    def test_manifest_has_packages(self):
        manifest = DependencyManifest.capture()
        assert len(manifest.packages) >= 1  # At least Python itself

    def test_manifest_has_python_version(self):
        manifest = DependencyManifest.capture()
        assert hasattr(manifest, "python_version")
        assert isinstance(manifest.python_version, str)

    def test_to_dict(self):
        manifest = DependencyManifest.capture()
        d = manifest.to_dict()
        assert "python_version" in d
        assert "packages" in d

    def test_packages_are_list(self):
        manifest = DependencyManifest.capture()
        assert isinstance(manifest.packages, list)


# ===========================================================================
# TestCitationRecord
# ===========================================================================

class TestCitationRecord:
    def _good_citation(self) -> CitationRecord:
        return CitationRecord(
            key="Good1965",
            title="Speculations Concerning the First Ultraintelligent Machine",
            authors=["I. J. Good"],
            year=1965,
            venue="Advances in Computers",
        )

    def test_fields(self):
        c = self._good_citation()
        assert c.key == "Good1965"
        assert c.year == 1965

    def test_to_bibtex(self):
        c = self._good_citation()
        bib = c.to_bibtex()
        assert isinstance(bib, str)
        assert "@" in bib
        assert "Good1965" in bib

    def test_to_dict(self):
        d = self._good_citation().to_dict()
        for k in ("key", "title", "authors", "year"):
            assert k in d


# ===========================================================================
# TestContributionChecklist
# ===========================================================================

class TestContributionChecklist:
    def test_default_has_15_items(self):
        cl = ContributionChecklist.default()
        assert len(cl.items) == 15

    def test_items_are_strings(self):
        cl = ContributionChecklist.default()
        for item in cl.items:
            assert isinstance(item, str)
            assert len(item) > 0

    def test_completeness_returns_float(self):
        cl = ContributionChecklist.default()
        score = cl.completeness()
        assert 0.0 <= score <= 1.0

    def test_to_dict(self):
        cl = ContributionChecklist.default()
        d = cl.to_dict()
        assert "items" in d
        assert "completeness" in d


# ===========================================================================
# TestReproducibilityPackage
# ===========================================================================

class TestReproducibilityPackage:
    def test_build_creates_files(self, tmp_path):
        pkg = _package(tmp_path)
        artefacts = pkg.build()
        assert len(artefacts) >= 1

    def test_build_creates_paper_outline(self, tmp_path):
        pkg = _package(tmp_path)
        pkg.build()
        expected = tmp_path / "PAPER_OUTLINE.md"
        assert expected.exists()

    def test_build_creates_reproduce_py(self, tmp_path):
        pkg = _package(tmp_path)
        pkg.build()
        expected = tmp_path / "reproduce.py"
        assert expected.exists()

    def test_build_creates_references_bib(self, tmp_path):
        pkg = _package(tmp_path)
        pkg.build()
        expected = tmp_path / "references.bib"
        assert expected.exists()

    def test_build_creates_manifest(self, tmp_path):
        pkg = _package(tmp_path)
        pkg.build()
        expected = tmp_path / "dependency_manifest.json"
        assert expected.exists()

    def test_build_creates_checklist(self, tmp_path):
        pkg = _package(tmp_path)
        pkg.build()
        expected = tmp_path / "CONTRIBUTION_CHECKLIST.md"
        assert expected.exists()

    def test_artefacts_list_has_6_items(self, tmp_path):
        pkg = _package(tmp_path)
        artefacts = pkg.build()
        assert len(artefacts) == 6

    def test_reproduce_py_is_valid_python(self, tmp_path):
        pkg = _package(tmp_path)
        pkg.build()
        code = (tmp_path / "reproduce.py").read_text()
        compile(code, "<string>", "exec")

    def test_references_bib_has_bibtex(self, tmp_path):
        pkg = _package(tmp_path)
        pkg.build()
        content = (tmp_path / "references.bib").read_text()
        assert "@" in content
        assert "Good1965" in content


# ===========================================================================
# TestWP70ExitCriteria
# ===========================================================================

class TestWP70ExitCriteria:
    def test_returns_dict(self):
        assert isinstance(verify_wp70_exit_criteria(), dict)

    def test_six_criteria(self):
        assert len(verify_wp70_exit_criteria()) == 6

    def test_all_pass_with_package(self, tmp_path):
        pkg = _package(tmp_path)
        result = verify_wp70_exit_criteria(pkg)
        for k, v in result.items():
            assert v, f"Criterion failed: '{k}'"

    def test_no_package_returns_dict(self):
        result = verify_wp70_exit_criteria(None)
        assert isinstance(result, dict)
        assert len(result) == 6


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration:
    def test_end_to_end_build(self, tmp_path):
        pkg = ReproducibilityPackage(
            output_dir=str(tmp_path),
            outline=PaperOutline.default(),
        )
        artefacts = pkg.build()
        assert len(artefacts) == 6
        for path in artefacts:
            assert os.path.exists(path), f"Artefact missing: {path}"

    def test_criteria_pass_after_build(self, tmp_path):
        pkg = _package(tmp_path)
        result = verify_wp70_exit_criteria(pkg)
        assert all(result.values()), f"Some criteria failed: {result}"
