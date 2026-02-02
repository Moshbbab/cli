"""
🏗️ HEMMAH ULTIMATE - Comprehensive real estate valuation system.
"""

from __future__ import annotations

import os
import sys
import warnings
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
import shap
import xgboost as xgb
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
from sklearn.model_selection import train_test_split
from IPython.display import HTML, clear_output, display
import ipywidgets as widgets

warnings.filterwarnings("ignore")

REQUIRED_PACKAGES = [
    "fpdf",
    "arabic-reshaper",
    "python-bidi",
    "shap",
    "xgboost",
    "plotly",
]


@dataclass
class PredictionResult:
    price_per_sqm: float
    confidence_interval: Tuple[float, float]
    model_name: str
    r2_score: float
    total_value: Optional[float] = None
    explanation: Optional[List[Dict[str, float]]] = None


class HemmahDataEngine:
    """معالجة البيانات بكفاءة عالية"""

    def __init__(self) -> None:
        self.raw_data: Optional[pd.DataFrame] = None
        self.processed_data: Optional[pd.DataFrame] = None
        self.quality_report: Dict[str, object] = {}

    def load(self, filepath: str) -> "HemmahDataEngine":
        """تحميل البيانات"""
        print(f"📂 تحميل: {filepath}")

        if filepath.endswith(".csv"):
            for enc in ["utf-8", "utf-8-sig", "cp1256", "iso-8859-1"]:
                try:
                    self.raw_data = pd.read_csv(filepath, encoding=enc)
                    break
                except Exception:
                    continue
        else:
            self.raw_data = pd.read_excel(filepath)

        if self.raw_data is None:
            raise ValueError("تعذر تحميل البيانات بالترميزات المتاحة")

        print(f"✅ تم تحميل {len(self.raw_data):,} سجل")
        return self

    def analyze_quality(self) -> Dict[str, object]:
        """فحص جودة البيانات"""
        if self.raw_data is None:
            raise ValueError("لا توجد بيانات محملة")

        df = self.raw_data
        self.quality_report = {
            "الإجمالي": len(df),
            "التكرارات": df.duplicated().sum(),
            "الاكتمال": f"{(df.notna().sum().mean() / len(df) * 100):.1f}%",
        }
        return self.quality_report

    def process(self) -> "HemmahDataEngine":
        """تنظيف وهندسة البيانات"""
        if self.raw_data is None:
            raise ValueError("لا توجد بيانات محملة")

        df = self.raw_data.copy()

        # تنظيف الأسعار والمساحات
        for col in df.columns:
            if any(x in col.lower() for x in ["price", "سعر", "value", "قيمة"]):
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
            if any(x in col.lower() for x in ["area", "مساحة"]):
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

        # إزالة القيم غير المنطقية
        df = df[df.select_dtypes(include=[np.number]).gt(0).all(axis=1)]

        # حساب سعر المتر
        price_cols = [c for c in df.columns if any(x in c.lower() for x in ["price", "سعر"])]
        area_cols = [c for c in df.columns if any(x in c.lower() for x in ["area", "مساحة"])]

        if price_cols and area_cols:
            df["price_per_sqm"] = df[price_cols[0]] / df[area_cols[0]]
            # إزالة الشواذ
            q1, q3 = df["price_per_sqm"].quantile([0.01, 0.99])
            df = df[(df["price_per_sqm"] >= q1) & (df["price_per_sqm"] <= q3)]

        self.processed_data = df
        print(f"✅ تم المعالجة: {len(df):,} سجل صالح")
        return self

    def get_features(self) -> Tuple[pd.DataFrame, List[str], str]:
        """إعداد المتغيرات للنمذجة"""
        if self.processed_data is None:
            raise ValueError("لا توجد بيانات معالجة")

        df = self.processed_data.copy()

        # الهدف
        target = "price_per_sqm" if "price_per_sqm" in df.columns else None
        if target is None:
            raise ValueError("لا يوجد عمود price_per_sqm في البيانات")

        # المتغيرات
        exclude = ["price", "سعر", "value", "قيمة", "price_per_sqm"]
        features = [
            c
            for c in df.columns
            if df[c].dtype in ["int64", "float64"]
            and not any(x in c.lower() for x in exclude)
        ]

        # إضافة متغيرات تصنيفية مشفرة
        cat_cols = [c for c in df.columns if df[c].dtype == "object"]
        for col in cat_cols[:2]:
            dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
            df = pd.concat([df, dummies], axis=1)
            features.extend(dummies.columns)

        model_df = df[features + [target]].dropna()

        return model_df, features, target


class HemmahMLEngine:
    """محرك التعلم الآلي المتقدم"""

    def __init__(self) -> None:
        self.model = None
        self.model_name: Optional[str] = None
        self.metrics: Dict[str, float] = {}
        self.explainer = None
        self.features: Optional[List[str]] = None

    def train(self, df: pd.DataFrame, features: List[str], target: str) -> "HemmahMLEngine":
        """تدريب النماذج"""
        print("🤖 تدريب النماذج...")

        x_data = df[features]
        y_data = df[target]
        self.features = features

        x_train, x_test, y_train, y_test = train_test_split(
            x_data, y_data, test_size=0.2, random_state=42
        )

        # اختبار نماذج متعددة
        candidates = {
            "XGBoost": xgb.XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.1),
            "Random Forest": RandomForestRegressor(n_estimators=200, max_depth=20),
            "Gradient Boosting": GradientBoostingRegressor(n_estimators=200),
        }

        best_score = -1.0

        for name, model in candidates.items():
            model.fit(x_train, y_train)
            score = model.score(x_test, y_test)

            if score > best_score:
                best_score = score
                self.model = model
                self.model_name = name

            print(f"  {name}: R² = {score:.3f}")

        if self.model is None:
            raise ValueError("فشل تدريب النماذج")

        # حساب المقاييس النهائية
        y_pred = self.model.predict(x_test)
        self.metrics = {
            "R²": r2_score(y_test, y_pred),
            "MAE": mean_absolute_error(y_test, y_pred),
            "MAPE": mean_absolute_percentage_error(y_test, y_pred) * 100,
        }

        print(f"\n✅ أفضل نموذج: {self.model_name}")
        print(f"   R² = {self.metrics['R²']:.3f} | MAPE = {self.metrics['MAPE']:.1f}%")

        # إعداد SHAP
        try:
            self.explainer = shap.TreeExplainer(self.model)
        except Exception:
            self.explainer = None

        return self

    def predict(self, inputs: pd.DataFrame) -> PredictionResult:
        """التنبؤ مع التفسير"""
        if self.model is None:
            raise ValueError("النموذج غير مدرب")

        pred = float(self.model.predict(inputs)[0])

        result = PredictionResult(
            price_per_sqm=pred,
            total_value=None,
            confidence_interval=(pred * 0.85, pred * 1.15),
            model_name=self.model_name or "",
            r2_score=self.metrics.get("R²", 0.0),
        )

        # SHAP
        if self.explainer is not None and self.features is not None:
            shap_vals = self.explainer.shap_values(inputs)
            values = shap_vals[0] if hasattr(shap_vals, "__len__") else shap_vals
            result.explanation = sorted(
                [
                    {
                        "feature": feat,
                        "impact": float(val),
                        "direction": "↑" if val > 0 else "↓",
                    }
                    for feat, val in zip(self.features, values)
                ],
                key=lambda x: abs(x["impact"]),
                reverse=True,
            )[:5]

        return result


class HemmahReporter:
    """مولد تقارير IVS 2025"""

    def __init__(self, data_engine: HemmahDataEngine, ml_engine: HemmahMLEngine) -> None:
        self.data = data_engine
        self.ml = ml_engine
        self.prediction: Optional[PredictionResult] = None

    def generate_pdf(self, property_data: Dict[str, str], output_name: Optional[str] = None) -> str:
        """توليد تقرير PDF رسمي"""
        if output_name is None:
            output_name = f"تقرير_تقييم_{datetime.now().strftime('%Y%m%d')}.pdf"

        self._ensure_fonts()

        pdf = FPDF()
        pdf.add_page()

        # الخطوط
        try:
            pdf.add_font("Amiri", "", "Amiri-Regular.ttf", uni=True)
            pdf.add_font("Amiri", "B", "Amiri-Bold.ttf", uni=True)
            font = "Amiri"
        except Exception:
            font = "Arial"

        # العنوان
        pdf.set_font(font, "B", 18)
        pdf.cell(0, 15, self._ar("تقرير تقييم عقاري رسمي"), 0, 1, "C")
        pdf.set_font(font, "", 12)
        pdf.cell(0, 10, self._ar(f"IVS 2025 Compliant | {date.today()}"), 0, 1, "C")
        pdf.line(10, 45, 200, 45)
        pdf.ln(10)

        # 1. نطاق العمل
        pdf.set_font(font, "B", 14)
        pdf.cell(0, 10, self._ar("1. نطاق العمل (Scope of Work)"), 0, 1, "R")
        pdf.set_font(font, "", 11)

        info = [
            f"التاريخ: {date.today()}",
            "الغرض: تقييم للرهن العقاري",
            "العميل: بنك [الاسم]",
            "المقيم: مشبب القحطاني",
            f"البيانات: {self.data.quality_report.get('الإجمالي', 0):,} صفقة",
        ]
        for line in info:
            pdf.cell(0, 8, self._ar(line), 0, 1, "R")

        pdf.ln(5)

        # 2. تفاصيل العقار
        pdf.set_font(font, "B", 14)
        pdf.cell(0, 10, self._ar("2. تفاصيل العقار المقيم"), 0, 1, "R")
        pdf.set_font(font, "", 11)

        for key, val in property_data.items():
            pdf.cell(0, 8, self._ar(f"{key}: {val}"), 0, 1, "R")

        pdf.ln(5)

        # 3. النتيجة
        if self.prediction:
            pdf.set_font(font, "B", 16)
            pdf.set_fill_color(230, 240, 255)
            pdf.cell(0, 12, self._ar("3. نتيجة التقييم"), 0, 1, "R", fill=True)

            pdf.set_font(font, "B", 14)
            price = self.prediction.price_per_sqm
            pdf.cell(0, 10, self._ar(f"السعر للمتر: {price:,.2f} ريال"), 0, 1, "C")

            if "المساحة" in property_data:
                total = price * float(property_data["المساحة"])
                pdf.set_font(font, "B", 18)
                pdf.set_text_color(0, 100, 0)
                pdf.cell(0, 12, self._ar(f"القيمة الإجمالية: {total:,.2f} ريال"), 0, 1, "C")
                pdf.set_text_color(0, 0, 0)

            pdf.set_font(font, "", 10)
            lower, upper = self.prediction.confidence_interval
            pdf.cell(
                0,
                8,
                self._ar(f"نطاق الثقة (±15%): {lower:,.0f} - {upper:,.0f} ريال/م²"),
                0,
                1,
                "C",
            )

        pdf.ln(10)

        # 4. التوقيع
        pdf.set_font(font, "B", 12)
        pdf.cell(0, 10, self._ar("المقيم المعتمد"), 0, 1, "C")
        pdf.cell(0, 10, self._ar("التوقيع: _________________"), 0, 1, "C")

        pdf.output(output_name)
        print(f"✅ تم إنشاء التقرير: {output_name}")

        return output_name

    def _ensure_fonts(self) -> None:
        if "google.colab" not in sys.modules:
            return
        if os.path.exists("Amiri-Regular.ttf") and os.path.exists("Amiri-Bold.ttf"):
            return

        os.system(
            "wget -q https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
        )
        os.system("wget -q https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf")

    def _ar(self, text: str) -> str:
        """معالجة النص العربي"""
        try:
            return get_display(arabic_reshaper.reshape(str(text)))
        except Exception:
            return str(text)

    def set_prediction(self, pred: PredictionResult) -> None:
        self.prediction = pred


class HemmahInterface:
    """واجهة المستخدم الكاملة"""

    def __init__(self, data_engine: HemmahDataEngine, ml_engine: HemmahMLEngine, reporter: HemmahReporter) -> None:
        self.data = data_engine
        self.ml = ml_engine
        self.reporter = reporter
        self.current_prediction: Optional[PredictionResult] = None

    def launch(self) -> None:
        """تشغيل الواجهة"""

        # العنوان
        display(
            HTML(
                """
        <div style="background: linear-gradient(90deg, #1e3c72, #2a5298); padding: 20px;
                    border-radius: 10px; color: white; text-align: center; margin-bottom: 20px;">
            <h1>🏗️ نظام همة للتقييم العقاري</h1>
            <h3>النسخة المتكاملة - IVS 2025</h3>
        </div>
        """
            )
        )

        # استخراج الأعمدة المتاحة
        if self.data.processed_data is None:
            raise ValueError("لا توجد بيانات معالجة")

        df = self.data.processed_data
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [c for c in numeric_cols if c != "price_per_sqm"]

        # إنشاء حقول الإدخال
        inputs: Dict[str, widgets.FloatSlider] = {}
        widgets_list: List[widgets.FloatSlider] = []

        for col in feature_cols[:6]:
            min_val = float(df[col].min())
            max_val = float(df[col].max())
            mean_val = float(df[col].mean())

            w = widgets.FloatSlider(
                value=mean_val,
                min=min_val,
                max=max_val,
                step=(max_val - min_val) / 100,
                description=f"{col}:",
                layout=widgets.Layout(width="100%"),
                style={"description_width": "150px"},
            )
            inputs[col] = w
            widgets_list.append(w)

        # أزرار التحكم
        btn_predict = widgets.Button(
            description="🚀 حساب التقييم",
            button_style="success",
            layout=widgets.Layout(width="48%", height="50px"),
        )

        btn_report = widgets.Button(
            description="📄 توليد تقرير PDF",
            button_style="primary",
            layout=widgets.Layout(width="48%", height="50px"),
        )

        output = widgets.Output()

        # دوال الأحداث
        def on_predict(_event) -> None:
            with output:
                clear_output()

                # إعداد المدخلات
                input_df = pd.DataFrame({k: [v.value] for k, v in inputs.items()})

                # التنبؤ
                result = self.ml.predict(input_df)
                self.current_prediction = result

                # حساب القيمة الإجمالية
                if "المساحة" in inputs:
                    area = inputs["المساحة"].value
                    result.total_value = result.price_per_sqm * area

                self.reporter.set_prediction(result)

                # العرض
                print("╔══════════════════════════════════════════════════════════╗")
                print("║                    نتيجة التقييم                          ║")
                print("╠══════════════════════════════════════════════════════════╣")
                print(f"║  السعر المتوقع للمتر:  {result.price_per_sqm:>15,.2f} ريال  ║")

                if result.total_value:
                    print(
                        f"║  القيمة الإجمالية:     {result.total_value:>15,.2f} ريال  ║"
                    )

                print(f"║  دقة النموذج (R²):     {result.r2_score:>15.3f}       ║")
                print(f"║  النموذج المستخدم:     {result.model_name:>15}       ║")
                print("╚══════════════════════════════════════════════════════════╝")

                # التفسير
                if result.explanation:
                    print("\n📊 تفسير العوامل المؤثرة:")
                    for item in result.explanation[:3]:
                        print(f"  {item['direction']} {item['feature']}: {item['impact']:+,.0f}")

        def on_report(_event) -> None:
            with output:
                if self.current_prediction is None:
                    print("❌ قم بالتقييم أولاً")
                    return

                property_data = {k: f"{v.value}" for k, v in inputs.items()}
                self.reporter.generate_pdf(property_data)

        btn_predict.on_click(on_predict)
        btn_report.on_click(on_report)

        # التجميع
        buttons = widgets.HBox([btn_predict, btn_report])
        display(widgets.VBox(widgets_list + [buttons, output]))


def run_hemmah_ultimate(file_path: str) -> Tuple[HemmahDataEngine, HemmahMLEngine, HemmahReporter, HemmahInterface]:
    """تشغيل النظام الكامل"""

    print("🏗️ بدء نظام همة المتكامل...")
    print("=" * 60)

    # 1. البيانات
    data = HemmahDataEngine()
    data.load(file_path)
    data.analyze_quality()
    data.process()

    # 2. ML
    ml = HemmahMLEngine()
    model_df, features, target = data.get_features()
    ml.train(model_df, features, target)

    # 3. التقارير
    reporter = HemmahReporter(data, ml)

    # 4. الواجهة
    ui = HemmahInterface(data, ml, reporter)
    ui.launch()

    return data, ml, reporter, ui


def _maybe_install_packages() -> None:
    if "google.colab" not in sys.modules:
        return

    print("🔧 جاري تثبيت المكتبات المطلوبة...")
    for pkg in REQUIRED_PACKAGES:
        os.system(f"pip install -q {pkg}")
    print("✅ تم التثبيت")


if __name__ == "__main__":
    _maybe_install_packages()

    FILE_PATH = "/mnt/kimi/upload/Transactions sale for real estate CSV.csv"
    run_hemmah_ultimate(FILE_PATH)
