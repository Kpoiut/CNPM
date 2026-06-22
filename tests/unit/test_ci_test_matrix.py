from pathlib import Path

from scripts.quality.export_ci_test_matrix import export_matrix, render_markdown


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_ci_matrix_export_is_workbook_driven_and_workflow_backed():
    result = export_matrix(
        PROJECT_ROOT / "docs" / "testing" / "AVM_Production_Test_Cases.xlsx",
        PROJECT_ROOT / ".github" / "workflows" / "ci.yml",
    )

    assert result["valid"], result["errors"]
    assert result["metrics"]["automated"] >= 20
    assert "backend-tests" in result["jobs"]
    assert "test-catalogue" in result["jobs"]
    assert any(
        command["local_command"] == "python -m pytest tests -q"
        for command in result["automated_commands"]
    )
    assert any(
        command["local_command"] == "python scripts/quality/validate_test_catalog.py"
        for command in result["automated_commands"]
    )

    markdown = render_markdown(result)
    assert "Production Test Catalogue Evidence" in markdown
    assert "Test Case ID" in markdown
    assert "backend-tests" in markdown
    assert "test-catalogue" in markdown
