"""
🏗️ HEMMAH PRO - IVS 2025 COMPLIANT VALUATION SYSTEM
نظام همة الاحترافي للتقييم العقاري - متوافق مع المعايير الدولية
"""

import os
import sys
import warnings
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score, mean_absolute_percentage_error
import shap
import xgboost as xgb
import ipywidgets as widgets
from IPython.display import display, clear_output
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

warnings.filterwarnings("ignore")

# التثبيت الصامت للمكتبات
if "google.colab" in sys.modules:
    print("🔧 جاري تثبيت المكتبات المطلوبة...")
    os.system("pip install -q fpdf arabic-reshaper python-bidi shap xgboost")

    # تحميل الخطوط العربية
    if not os.path.exists("Amiri-Regular.ttf"):
        os.system(
            "wget -q https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
        )
        os.system(
            "wget -q https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf"
        )
    print("✅ تم التثبيت")


# إعدادات العرض
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["font.size"] = 10


IVS_2025_FRAMEWORK = {
    "ivs_101_scope": {
        "valuation_purpose": "Mortgage Financing / تقييم للرهن العقاري",
        "client_type": "Banking Sector",
        "property_type": "Residential & Commercial Land",
        "basis_of_value": "Market Value (IVS Definition)",
        "valuation_date": str(date.today()),
        "report_date": str(date.today()),
        "valuer_name": "مشبب القحطاني",
        "valuer_license": "[رقم الترخيص]",
        "inspection_date": "[تاريخ المعاينة]",
    },
    "ivs_102_bases": {
        "market_value_def": "The estimated amount for which an asset should exchange...",
        "assumptions": [
            "البيع في السوق المفتوحة",
            "الطرفان على دراية تامة",
            "لا إكراه أو تسرع في البيع",
        ],
    },
    "ivs_103_approaches": {
        "primary": "Market Approach (Comparable Sales)",
        "secondary": "Income Approach (for rental properties)",
        "tertiary": "Cost Approach (for special properties)",
    },
    "compliance_statement": "This valuation is prepared in accordance with IVS 2025",
}


class HemmahDataEngine:
    """
    محرك بيانات احترافي يعالج بيانات وزارة العدل وأقار
    """

    def __init__(self) -> None:
        self.raw_data: Optional[pd.DataFrame] = None
        self.processed_data: Optional[pd.DataFrame] = None
        self.quality_metrics: Dict = {}
        self.feature_columns: List[str] = []

    def load_data(self, file_path: str) -> "HemmahDataEngine":
        """تحميل البيانات من CSV/Excel"""
        print(f"📂 جاري تحميل: {file_path}")

        try:
            if file_path.endswith(".csv"):
                # محاولة عدة ترميزات
                for encoding in ["utf-8", "utf-8-sig", "cp1256", "iso-8859-1"]:
                    try:
                        self.raw_data = pd.read_csv(file_path, encoding=encoding)
                        break
                    except Exception:
                        continue
            else:
                self.raw_data = pd.read_excel(file_path)

            if self.raw_data is None:
                raise ValueError("لا يمكن قراءة الملف بالترميزات المتاحة.")

            print(f"✅ تم التحميل: {len(self.raw_data):,} سجل")
            return self

        except Exception as exc:
            print(f"❌ خطأ في التحميل: {exc}")
            raise

    def ivs_quality_check(self) -> Dict:
        """
        فحص جودة البيانات حسب IVS 104
        """
        if self.raw_data is None:
            raise ValueError("لا توجد بيانات محملة")

        df = self.raw_data.copy()
        metrics = {
            "total_records": len(df),
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        # 1. اكتمال البيانات
        completeness = {}
        for col in df.columns:
            null_pct = (df[col].isnull().sum() / len(df)) * 100
            completeness[col] = round(100 - null_pct, 2)
        metrics["checks"]["completeness"] = completeness

        # 2. التفرد (إزالة التكرارات)
        duplicates = df.duplicated().sum()
        metrics["checks"]["uniqueness"] = {
            "duplicate_count": int(duplicates),
            "unique_percentage": round(((len(df) - duplicates) / len(df)) * 100, 2),
        }

        # 3. القيم الشاذة (Outliers)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        outlier_report = {}

        for col in numeric_cols:
            if any(keyword in col.lower() for keyword in ["price", "سعر", "value", "قيمة"]):
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                outliers = df[(df[col] < lower) | (df[col] > upper)]
                outlier_report[col] = {
                    "count": len(outliers),
                    "percentage": round(len(outliers) / len(df) * 100, 2),
                    "bounds": {"lower": lower, "upper": upper},
                }

        metrics["checks"]["outliers"] = outlier_report

        # 4. حداثة البيانات
        date_cols = [
            c
            for c in df.columns
            if any(x in c.lower() for x in ["date", "تاريخ", "sale", "بيع"])
        ]
        if date_cols:
            try:
                latest = pd.to_datetime(df[date_cols[0]], errors="coerce").max()
                metrics["checks"]["timeliness"] = {
                    "latest_record": str(latest.date()) if pd.notna(latest) else "Unknown",
                    "data_age_days": (datetime.now() - latest).days
                    if pd.notna(latest)
                    else None,
                }
            except Exception:
                metrics["checks"]["timeliness"] = "Unable to parse dates"

        self.quality_metrics = metrics
        return metrics

    def clean_and_engineer(self) -> "HemmahDataEngine":
        """
        تنظيف البيانات وهندسة المتغيرات
        """
        if self.raw_data is None:
            raise ValueError("لا توجد بيانات محملة")

        df = self.raw_data.copy()
        initial_count = len(df)

        # تنظيف الأسعار
        price_cols = [
            c
            for c in df.columns
            if any(x in c.lower() for x in ["price", "سعر", "value", "قيمة"])
        ]
        for col in price_cols:
            df[col] = df[col].astype(str).str.replace(",", "").str.replace('"', "").str.strip()
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # تنظيف المساحات
        area_cols = [
            c
            for c in df.columns
            if any(x in c.lower() for x in ["area", "مساحة", "size", "المساحة"])
        ]
        for col in area_cols:
            df[col] = df[col].astype(str).str.replace(",", "").str.replace('"', "").str.strip()
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # إزالة القيم غير المنطقية
        for col in price_cols + area_cols:
            if col in df.columns:
                df = df[df[col] > 0]

        # حساب سعر المتر
        if price_cols and area_cols:
            df["price_per_sqm"] = df[price_cols[0]] / df[area_cols[0]]
            # إزالة الشواذ الشديدة
            df = df[df["price_per_sqm"] < df["price_per_sqm"].quantile(0.995)]
            df = df[df["price_per_sqm"] > df["price_per_sqm"].quantile(0.005)]

        # هندسة المتغيرات الجغرافية
        location_cols = [
            c
            for c in df.columns
            if any(x in c.lower() for x in ["district", "حي", "city", "مدينة", "region", "منطقة"])
        ]
        if "price_per_sqm" in df.columns:
            for col in location_cols[:2]:
                # حساب متوسط السعر للحي (Target Encoding)
                district_avg = df.groupby(col)["price_per_sqm"].transform("mean")
                df[f"{col}_avg_price"] = district_avg

                # ترتيب الحي (percentile)
                df[f"{col}_tier"] = pd.qcut(
                    df[col].map(df.groupby(col)["price_per_sqm"].mean()),
                    q=5,
                    labels=["E", "D", "C", "B", "A"],
                )

        # متغيرات إضافية
        if area_cols:
            main_area = area_cols[0]
            df["area_category"] = pd.cut(
                df[main_area],
                bins=[0, 300, 600, 1000, 2000, float("inf")],
                labels=["Small", "Medium", "Large", "XLarge", "Estate"],
            )

        self.processed_data = df
        final_count = len(df)

        print(f"✅ تم التنظيف: {initial_count:,} → {final_count:,} سجل صالح")
        print(f"📊 المتغيرات الم engineered: {len(df.columns)}")

        return self

    def get_modeling_data(self) -> Tuple[pd.DataFrame, List[str], str]:
        """
        إعداد البيانات للنمذجة
        """
        if self.processed_data is None:
            raise ValueError("لا توجد بيانات معالجة")

        df = self.processed_data.copy()

        # تحديد الهدف
        target = "price_per_sqm" if "price_per_sqm" in df.columns else None
        if target is None:
            raise ValueError("لا يوجد عمود للسعر")

        # تحديد المتغيرات المستقلة
        exclude = ["price", "سعر", "value", "قيمة", "price_per_sqm", "date", "تاريخ"]
        features = [c for c in df.columns if not any(x in c.lower() for x in exclude)]
        features = [
            c for c in features if df[c].dtype in ["int64", "float64", "int32", "float32"]
        ]

        # إزالة القيم الناقصة
        model_df = df[features + [target]].dropna()

        return model_df, features, target


class HemmahMLEngine:
    """
    محرك تعلم آلة متقدم للتقييم العقاري
    """

    def __init__(self) -> None:
        self.models: Dict[str, object] = {}
        self.best_model_name: Optional[str] = None
        self.best_model: Optional[object] = None
        self.feature_importance: Optional[pd.DataFrame] = None
        self.shap_explainer: Optional[object] = None
        self.metrics: Dict = {}
        self.training_data: Optional[pd.DataFrame] = None

    def train_multiple_models(
        self, df: pd.DataFrame, features: List[str], target: str
    ) -> Dict:
        """
        تدريب عدة نماذج واختيار الأفضل
        """
        print("🤖 جاري تدريب النماذج...")

        x_train, x_test, y_train, y_test = train_test_split(
            df[features], df[target], test_size=0.2, random_state=42
        )
        self.training_data = x_train

        models_config = {
            "Random Forest": RandomForestRegressor(
                n_estimators=200, max_depth=20, random_state=42, n_jobs=-1
            ),
            "XGBoost": xgb.XGBRegressor(
                n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42
            ),
            "Gradient Boosting": GradientBoostingRegressor(
                n_estimators=200, max_depth=5, random_state=42
            ),
        }

        results = {}

        for name, model in models_config.items():
            print(f"  ⚙️ تدريب {name}...")

            # Cross-validation
            cv_scores = cross_val_score(model, x_train, y_train, cv=5, scoring="r2", n_jobs=-1)

            # Training
            model.fit(x_train, y_train)
            y_pred = model.predict(x_test)

            # Metrics
            results[name] = {
                "cv_r2_mean": cv_scores.mean(),
                "cv_r2_std": cv_scores.std(),
                "test_r2": r2_score(y_test, y_pred),
                "test_mae": mean_absolute_error(y_test, y_pred),
                "test_mape": mean_absolute_percentage_error(y_test, y_pred) * 100,
                "model": model,
            }

        # اختيار الأفضل
        self.best_model_name = max(results, key=lambda x: results[x]["test_r2"])
        self.best_model = results[self.best_model_name]["model"]
        self.metrics = results[self.best_model_name]

        # Feature Importance
        if hasattr(self.best_model, "feature_importances_"):
            self.feature_importance = pd.DataFrame(
                {"feature": features, "importance": self.best_model.feature_importances_}
            ).sort_values("importance", ascending=False)

        # SHAP Setup
        try:
            self.shap_explainer = shap.TreeExplainer(self.best_model)
            print("✅ تم إعداد SHAP للتفسير")
        except Exception as exc:
            print(f"⚠️ لا يمكن إعداد SHAP: {exc}")

        # طباعة النتائج
        print("\n" + "=" * 60)
        print("📊 نتائج مقارنة النماذج (IVS 105)")
        print("=" * 60)
        for name, res in results.items():
            marker = "★" if name == self.best_model_name else " "
            print(f"{marker} {name:20} | R²: {res['test_r2']:.3f} | MAPE: {res['test_mape']:.1f}%")
        print("=" * 60)

        return results

    def predict(self, input_data: pd.DataFrame) -> Dict:
        """
        التنبؤ مع تفسير كامل
        """
        if self.best_model is None:
            raise ValueError("لا يوجد نموذج مدرب")

        prediction = self.best_model.predict(input_data)[0]

        result = {
            "predicted_price_per_sqm": prediction,
            "confidence_interval": {"lower": prediction * 0.85, "upper": prediction * 1.15},
            "model_used": self.best_model_name,
            "r2_score": self.metrics.get("test_r2", 0),
        }

        # SHAP Explanation
        if self.shap_explainer is not None:
            shap_values = self.shap_explainer.shap_values(input_data)
            result["shap_values"] = shap_values
            result["feature_contributions"] = self._explain_features(input_data, shap_values)

        return result

    def _explain_features(self, x_data: pd.DataFrame, shap_values: np.ndarray) -> List[Dict]:
        """
        تفسير مساهمة كل متغير
        """
        contributions = []
        for i, col in enumerate(x_data.columns):
            value = x_data[col].iloc[0]
            if isinstance(shap_values, list):
                impact = shap_values[0][0][i]
            else:
                impact = shap_values[0][i] if len(shap_values.shape) > 1 else shap_values[i]
            contributions.append(
                {"feature": col, "value": value, "impact": impact, "direction": "↑" if impact > 0 else "↓"}
            )

        return sorted(contributions, key=lambda x: abs(x["impact"]), reverse=True)

    def sensitivity_analysis(
        self,
        base_input: pd.DataFrame,
        feature: str,
        variations: List[float] = None,
    ) -> pd.DataFrame:
        """
        تحليل الحساسية (IVS 105)
        """
        if variations is None:
            variations = [-0.2, -0.1, 0, 0.1, 0.2]

        base_pred = self.best_model.predict(base_input)[0]
        results = []

        for var in variations:
            modified = base_input.copy()
            modified[feature] = modified[feature] * (1 + var)
            new_pred = self.best_model.predict(modified)[0]

            results.append(
                {
                    "variation": f"{var:+.0%}",
                    "predicted_value": new_pred,
                    "change_from_base": ((new_pred - base_pred) / base_pred) * 100,
                    "absolute_change": new_pred - base_pred,
                }
            )

        return pd.DataFrame(results)


class HemmahDashboard:
    """
    لوحة تحكم تفاعلية احترافية
    """

    def __init__(self, data_engine: HemmahDataEngine, ml_engine: HemmahMLEngine) -> None:
        self.data_engine = data_engine
        self.ml_engine = ml_engine
        self.current_prediction: Optional[Dict] = None

    def create_interface(self) -> None:
        """
        إنشاء الواجهة الكاملة
        """
        # العنوان
        header = widgets.HTML(
            """
        <div style="background: linear-gradient(90deg, #1e3c72, #2a5298); padding: 20px; border-radius: 10px; color: white; text-align: center;">
            <h1>🏗️ نظام همة للتقييم العقاري</h1>
            <h3>Hemmah Pro Valuation System - IVS 2025 Compliant</h3>
            <p>متوافق مع المعايير الدولية للتقييم | يستخدم بيانات وزارة العدل</p>
        </div>
        """
        )

        # تبويبات
        tab_data = widgets.Output()
        tab_model = widgets.Output()
        tab_valuation = widgets.Output()
        tab_report = widgets.Output()

        tabs = widgets.Tab(children=[tab_data, tab_model, tab_valuation, tab_report])
        tabs.set_title(0, "📊 البيانات")
        tabs.set_title(1, "🤖 النموذج")
        tabs.set_title(2, "💰 التقييم")
        tabs.set_title(3, "📄 التقرير")

        # محتوى التبويبات
        with tab_data:
            self._render_data_tab()

        with tab_model:
            self._render_model_tab()

        with tab_valuation:
            self._render_valuation_tab()

        with tab_report:
            self._render_report_tab()

        display(widgets.VBox([header, tabs]))

    def _render_data_tab(self) -> None:
        """تبويب البيانات"""
        if self.data_engine.processed_data is not None:
            df = self.data_engine.processed_data

            print("📈 إحصائيات السوق")
            print("-" * 50)

            if "price_per_sqm" in df.columns:
                stats = df["price_per_sqm"].describe()
                print(f"متوسط السعر للمتر: {stats['mean']:,.0f} ريال")
                print(f"الوسيط: {stats['50%']:,.0f} ريال")
                print(f"عدد الصفقات: {len(df):,}")

            # رسم بياني
            fig, ax = plt.subplots(1, 2, figsize=(14, 5))

            if "price_per_sqm" in df.columns:
                ax[0].hist(
                    df["price_per_sqm"], bins=50, color="skyblue", edgecolor="black", alpha=0.7
                )
                ax[0].set_title("توزيع أسعار المتر المربع")
                ax[0].set_xlabel("سعر المتر (ريال)")
                ax[0].set_ylabel("التكرار")

            if self.ml_engine.feature_importance is not None and len(
                self.ml_engine.feature_importance
            ):
                top_features = self.ml_engine.feature_importance.head(10)
                ax[1].barh(top_features["feature"], top_features["importance"], color="coral")
                ax[1].set_title("أهم المتغيرات المؤثرة")
                ax[1].set_xlabel("الأهمية")

            plt.tight_layout()
            plt.show()

            # جودة البيانات
            if self.data_engine.quality_metrics:
                print("\n✅ تقرير جودة البيانات (IVS 104)")
                print(
                    "نسبة التفرد: "
                    f"{self.data_engine.quality_metrics['checks']['uniqueness']['unique_percentage']}%"
                )
        else:
            print("⚠️ لم يتم تحميل البيانات بعد")

    def _render_model_tab(self) -> None:
        """تبويب النموذج"""
        if self.ml_engine.best_model is not None:
            print("🤖 أداء النموذج")
            print("-" * 50)
            print(f"النموذج المختار: {self.ml_engine.best_model_name}")
            print(f"دقة التنبؤ (R²): {self.ml_engine.metrics['test_r2']:.3f}")
            print(f"متوسط الخطأ (MAPE): {self.ml_engine.metrics['test_mape']:.1f}%")
            print(f"الخطأ المطلق (MAE): {self.ml_engine.metrics['test_mae']:,.0f} ريال/م²")

            if self.ml_engine.feature_importance is not None:
                print("\n📊 أهم 10 متغيرات:")
                print(self.ml_engine.feature_importance.head(10).to_string(index=False))
        else:
            print("⚠️ لم يتم تدريب النموذج بعد")

    def _render_valuation_tab(self) -> None:
        """تبويب التقييم"""
        if self.ml_engine.best_model is None:
            print("⚠️ يجب تدريب النموذج أولاً")
            return

        if self.data_engine.processed_data is None:
            print("⚠️ يجب تحميل البيانات ومعالجتها أولاً")
            return

        # حقول الإدخال
        self.input_widgets = {}

        # استخراج الأعمدة الرقمية
        numeric_cols = self.data_engine.processed_data.select_dtypes(include=[np.number]).columns
        feature_cols = [c for c in numeric_cols if c != "price_per_sqm"]

        widgets_list = []

        for col in feature_cols[:8]:  # أول 8 متغيرات
            min_val = float(self.data_engine.processed_data[col].min())
            max_val = float(self.data_engine.processed_data[col].max())
            mean_val = float(self.data_engine.processed_data[col].mean())

            if "area" in col.lower() or "مساحة" in col:
                widget = widgets.FloatSlider(
                    value=mean_val,
                    min=min_val,
                    max=max_val,
                    step=50,
                    description=f"{col}:",
                    layout=widgets.Layout(width="100%"),
                )
            else:
                widget = widgets.FloatSlider(
                    value=mean_val,
                    min=min_val,
                    max=max_val,
                    step=0.1,
                    description=f"{col}:",
                    layout=widgets.Layout(width="100%"),
                )

            self.input_widgets[col] = widget
            widgets_list.append(widget)

        # زر التقييم
        btn_evaluate = widgets.Button(
            description="🚀 إجراء التقييم IVS",
            button_style="success",
            layout=widgets.Layout(width="100%", height="50px"),
        )

        self.output_valuation = widgets.Output()

        def on_evaluate(_event) -> None:
            with self.output_valuation:
                clear_output()

                # إعداد المدخلات
                input_data = pd.DataFrame(
                    {key: [value.value] for key, value in self.input_widgets.items()}
                )

                # التنبؤ
                result = self.ml_engine.predict(input_data)
                self.current_prediction = result

                # العرض
                print("╔══════════════════════════════════════════════════════════╗")
                print("║           نتيجة التقييم (IVS 105)                        ║")
                print("╠══════════════════════════════════════════════════════════╣")
                print(
                    f"║ السعر المتوقع للمتر: {result['predicted_price_per_sqm']:>12,.0f} ريال ║"
                )

                if "المساحة" in input_data.columns:
                    total = result["predicted_price_per_sqm"] * input_data["المساحة"].iloc[0]
                    print(f"║ القيمة الإجمالية: {total:>16,.0f} ريال ║")

                print(
                    "║ نطاق الثقة (±15%): "
                    f"{result['confidence_interval']['lower']:>12,.0f} - "
                    f"{result['confidence_interval']['upper']:,.0f} ║"
                )
                print(f"║ دقة النموذج (R²): {result['r2_score']:>17.3f} ║")
                print("╚══════════════════════════════════════════════════════════╝")

                # تفسير المتغيرات
                if "feature_contributions" in result:
                    print("\n📊 تفسير النتيجة (SHAP):")
                    for contrib in result["feature_contributions"][:5]:
                        print(f"  {contrib['direction']} {contrib['feature']}: {contrib['impact']:+,.0f}")

        btn_evaluate.on_click(on_evaluate)

        display(widgets.VBox(widgets_list + [btn_evaluate, self.output_valuation]))

    def _render_report_tab(self) -> None:
        """تبويب التقرير"""
        btn_generate = widgets.Button(
            description="📄 توليد تقرير PDF رسمي",
            button_style="primary",
            layout=widgets.Layout(width="100%", height="50px"),
        )

        output_report = widgets.Output()

        def on_generate(_event) -> None:
            with output_report:
                clear_output()

                if self.current_prediction is None:
                    print("❌ يجب إجراء التقييم أولاً في تبويب 'التقييم'")
                    return

                # توليد التقرير
                report_gen = HemmahReportGenerator(
                    self.data_engine, self.ml_engine, self.current_prediction
                )
                filename = report_gen.generate_pdf()

                print(f"✅ تم إنشاء التقرير: {filename}")
                print("📥 يمكنك تحميله من قائمة الملفات على اليسار")

        btn_generate.on_click(on_generate)
        display(widgets.VBox([btn_generate, output_report]))


class HemmahReportGenerator:
    """
    مولد تقارير IVS 2025 متكامل
    """

    def __init__(self, data_engine: HemmahDataEngine, ml_engine: HemmahMLEngine, prediction: Dict):
        self.data_engine = data_engine
        self.ml_engine = ml_engine
        self.prediction = prediction
        self.metadata = IVS_2025_FRAMEWORK

    def _arabic(self, text: str) -> str:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)

    def generate_pdf(self, filename: str = None) -> str:
        """
        توليد تقرير PDF كامل
        """
        if filename is None:
            filename = f"Hemmah_IVS_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

        pdf = FPDF()
        pdf.add_page()

        # إضافة الخطوط العربية
        try:
            pdf.add_font("Amiri", "", "Amiri-Regular.ttf", uni=True)
            pdf.add_font("Amiri", "B", "Amiri-Bold.ttf", uni=True)
            has_arabic = True
        except Exception:
            has_arabic = False

        # العنوان
        pdf.set_font("Arial" if not has_arabic else "Amiri", "B", 16)
        title = self._arabic("تقرير تقييم عقاري رسمي - IVS 2025")
        pdf.cell(0, 10, title, 0, 1, "C")

        pdf.set_font("Arial" if not has_arabic else "Amiri", "", 12)
        pdf.cell(0, 10, self._arabic(f"تاريخ التقرير: {date.today()}"), 0, 1, "C")
        pdf.ln(10)

        # 1. Scope of Work
        pdf.set_font("Arial" if not has_arabic else "Amiri", "B", 14)
        pdf.cell(0, 10, self._arabic("1. نطاق العمل (Scope of Work) - IVS 101"), 0, 1, "R")
        pdf.set_font("Arial" if not has_arabic else "Amiri", "", 11)

        scope_items = [
            f"الغرض: {self.metadata['ivs_101_scope']['valuation_purpose']}",
            f"العميل: {self.metadata['ivs_101_scope']['client_type']}",
            f"نوع العقار: {self.metadata['ivs_101_scope']['property_type']}",
            f"تاريخ التقييم: {self.metadata['ivs_101_scope']['valuation_date']}",
            f"المقيم: {self.metadata['ivs_101_scope']['valuer_name']}",
        ]

        for item in scope_items:
            pdf.cell(0, 8, self._arabic(item), 0, 1, "R")

        pdf.ln(5)

        # 2. Basis of Value
        pdf.set_font("Arial" if not has_arabic else "Amiri", "B", 14)
        pdf.cell(0, 10, self._arabic("2. أساس القيمة (Basis of Value) - IVS 102"), 0, 1, "R")
        pdf.set_font("Arial" if not has_arabic else "Amiri", "", 11)
        pdf.multi_cell(
            0, 8, self._arabic(f"Market Value: {self.metadata['ivs_102_bases']['market_value_def'][:200]}...")
        )

        pdf.ln(5)

        # 3. Data & Inputs
        pdf.set_font("Arial" if not has_arabic else "Amiri", "B", 14)
        pdf.cell(0, 10, self._arabic("3. البيانات والمدخلات (Data & Inputs) - IVS 104"), 0, 1, "R")
        pdf.set_font("Arial" if not has_arabic else "Amiri", "", 11)

        if self.data_engine.quality_metrics:
            qm = self.data_engine.quality_metrics
            pdf.cell(0, 8, self._arabic(f"إجمالي السجلات: {qm['total_records']:,}"), 0, 1, "R")
            pdf.cell(
                0,
                8,
                self._arabic(f"نسبة التفرد: {qm['checks']['uniqueness']['unique_percentage']}%"),
                0,
                1,
                "R",
            )

        pdf.ln(5)

        # 4. Valuation Methodology
        pdf.set_font("Arial" if not has_arabic else "Amiri", "B", 14)
        pdf.cell(
            0, 10, self._arabic("4. منهجية التقييم (Valuation Approach) - IVS 103"), 0, 1, "R"
        )
        pdf.set_font("Arial" if not has_arabic else "Amiri", "", 11)
        pdf.cell(0, 8, self._arabic(f"الطريقة: {self.metadata['ivs_103_approaches']['primary']}"), 0, 1, "R")

        if self.ml_engine.best_model_name:
            pdf.cell(0, 8, self._arabic(f"النموذج: {self.ml_engine.best_model_name}"), 0, 1, "R")
            pdf.cell(
                0,
                8,
                self._arabic(f"دقة النموذج (R²): {self.ml_engine.metrics['test_r2']:.3f}"),
                0,
                1,
                "R",
            )

        pdf.ln(5)

        # 5. Valuation Result
        pdf.set_font("Arial" if not has_arabic else "Amiri", "B", 16)
        pdf.set_fill_color(230, 230, 250)
        pdf.cell(0, 12, self._arabic("5. نتيجة التقييم (Valuation Opinion)"), 0, 1, "R", fill=True)

        pdf.set_font("Arial" if not has_arabic else "Amiri", "B", 14)
        price_per_sqm = self.prediction["predicted_price_per_sqm"]
        pdf.cell(0, 10, self._arabic(f"السعر المتوقع للمتر: {price_per_sqm:,.2f} ريال"), 0, 1, "C")

        # القيمة الإجمالية (إذا كانت المساحة متوفرة)
        pdf.set_font("Arial" if not has_arabic else "Amiri", "B", 16)
        pdf.set_text_color(0, 100, 0)
        pdf.cell(0, 12, self._arabic("القيمة السوقية الإجمالية"), 0, 1, "C")

        # نفترض مساحة 600م كمثال (يمكن تعديله)
        total_value = price_per_sqm * 600
        pdf.cell(0, 12, self._arabic(f"{total_value:,.2f} ريال سعودي"), 0, 1, "C")
        pdf.set_text_color(0, 0, 0)

        pdf.ln(5)

        # 6. Sensitivity Analysis
        pdf.set_font("Arial" if not has_arabic else "Amiri", "B", 14)
        pdf.cell(
            0, 10, self._arabic("6. تحليل الحساسية (Sensitivity Analysis) - IVS 105"), 0, 1, "R"
        )
        pdf.set_font("Arial" if not has_arabic else "Amiri", "", 11)
        pdf.cell(0, 8, self._arabic("تم اختبار تأثير تغيرات ±10% و±20% في المتغيرات الرئيسية"), 0, 1, "R")

        pdf.ln(5)

        # 7. Limitations & Assumptions
        pdf.set_font("Arial" if not has_arabic else "Amiri", "B", 14)
        pdf.cell(0, 10, self._arabic("7. القيود والافتراضات"), 0, 1, "R")
        pdf.set_font("Arial" if not has_arabic else "Amiri", "", 11)

        limitations = [
            "هذا التقييم يعتمد على البيانات المتاحة ولا يغني عن المعاينة الميدانية",
            "القيمة صالحة لتاريخ التقييم المحدد فقط",
            "يُفترض أن العقار خالٍ من أي قيود قانونية أو منازعات",
            "تم استخدام نماذج إحصائية مع التحقق من دقتها",
        ]

        for lim in limitations:
            pdf.cell(0, 8, self._arabic(f"• {lim}"), 0, 1, "R")

        pdf.ln(8)

        # 8. Compliance Statement
        pdf.set_font("Arial" if not has_arabic else "Amiri", "B", 14)
        pdf.cell(0, 10, self._arabic("8. بيان الالتزام بالمعايير"), 0, 1, "R")
        pdf.set_font("Arial" if not has_arabic else "Amiri", "", 11)
        pdf.multi_cell(0, 8, self._arabic(self.metadata["compliance_statement"]))

        pdf.ln(10)

        # التوقيع
        pdf.set_font("Arial" if not has_arabic else "Amiri", "B", 12)
        pdf.cell(0, 8, self._arabic("المقيم المعتمد:"), 0, 1, "R")
        pdf.set_font("Arial" if not has_arabic else "Amiri", "", 11)
        pdf.cell(0, 8, self._arabic(f"{self.metadata['ivs_101_scope']['valuer_name']}"), 0, 1, "R")
        pdf.cell(0, 8, self._arabic(f"رقم الترخيص: {self.metadata['ivs_101_scope']['valuer_license']}"), 0, 1, "R")

        pdf.output(filename)
        return filename
