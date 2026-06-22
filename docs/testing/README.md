# Production Test Suite

`AVM_Production_Test_Cases.xlsx` là catalogue và release gate hiện hành:

- 122 `Test Case ID` duy nhất, STT liên tục.
- 122 happy-path scenarios.
- 244 failure-path scenarios; mỗi scenario có điều kiện kích hoạt, expected result và recovery riêng.
- Tách `Design Status`, `Automation Status` và `Execution Status`.
- Có Requirement ID, Risk Category, fixture, environment, owner/reviewer, commit SHA, evidence URL và defect ID.
- Có RTM, automation mapping, audit closure và release dashboard.

Kiểm tra contract workbook:

```bash
python scripts/quality/validate_test_catalog.py \
  --report reports/test-catalogue-validation.json
```

Ba suite demo có kịch bản ngay trong file:

```bash
pytest tests/production/test_database_release_gate.py -vv
pytest tests/production/test_api_release_gate.py -vv
pytest tests/production/test_ml_release_gate.py -vv
```

GitHub Actions chạy toàn bộ `tests/`, frontend unit tests, frontend bundle budget gate, workbook validator, dependency audit và Docker smoke. Mỗi job upload JUnit/coverage/log/catalog/bundle evidence theo commit SHA; SonarCloud là quality gate bên thứ ba.
