# Model Artifact Policy

Runtime chỉ load artifact được pin bởi `ACTIVE_MODEL.json`. Loader không fallback sang latest/candidate/legacy `.pkl`.

Giữ trong workspace:

- `model_20260504_144753.pkl`: production active model, MAPE 16.0864%, MAE 776,510,800 VND.
- `model_20260621_162930.pkl`: latest candidate để benchmark, chưa active vì MAPE 44.3777%.
- `metadata_*.json`: metric và lineage lịch sử, kích thước nhỏ nên giữ để audit.
- `shap_global_cache.json`: cache explainability cho active/latest pipeline.

Không thêm lại `model_pipeline.pkl`, `randomforest_model.pkl` hoặc baseline `.pkl` cũ. Nếu cần rollback, tạo `ACTIVE_MODEL.json` trỏ tới artifact đã được kiểm chứng và còn tồn tại.
