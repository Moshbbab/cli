# Hemmah Pro IVS 2025: CSV ➜ PDF Example

This is a minimal, reproducible local run that takes a CSV input and produces a PDF report using `hemmah_pro_ivs_2025.py`.

## 1) Install Python dependencies

```bash
pip install pandas numpy matplotlib scikit-learn shap xgboost ipywidgets ipython fpdf arabic-reshaper python-bidi
```

## 2) Use the sample CSV

A ready-to-run test dataset is included at:

```
docs/hemmah_sample.csv
```

The minimum required columns are:
- `price` (or any column containing `price/سعر/value/قيمة`)
- `area` (or any column containing `area/مساحة/size/المساحة`)

## 3) Run the end-to-end script

From the repo root:

```bash
python - <<'PY'
from hemmah_pro_ivs_2025 import HemmahDataEngine, HemmahMLEngine, HemmahReportGenerator

engine = HemmahDataEngine()
engine.load_data("docs/hemmah_sample.csv")
engine.ivs_quality_check()
engine.clean_and_engineer()
model_df, features, target = engine.get_modeling_data()

ml = HemmahMLEngine()
ml.train_multiple_models(model_df, features, target)

sample_input = model_df[features].head(1)
result = ml.predict(sample_input)

report = HemmahReportGenerator(engine, ml, result)
pdf_name = report.generate_pdf("Hemmah_Test_Report.pdf")

print("PDF generated:", pdf_name)
PY
```

## 4) Output

You should see training output in the console, and a PDF named:

```
Hemmah_Test_Report.pdf
```

in the current working directory.

## Notes on resource loading

- The PDF generator tries to load `Amiri-Regular.ttf` and `Amiri-Bold.ttf` from the current working directory. If they are not present, the report falls back to Latin-1 safe English text to avoid `UnicodeEncodeError` in FPDF.
- This module does not currently use Jinja2 templates; all report content is built in code.
