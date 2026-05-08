import { useMemo, useState } from "react";

type ChecklistItem = {
  name: string;
  found: boolean;
  standard: "IVS" | "IFRS 13";
};

const ivsElements = [
  "الغرض من التقييم",
  "تاريخ التقييم",
  "أساس القيمة",
  "افتراضات خاصة",
  "نطاق العمل",
];

const ifrs13Elements = [
  "الافتراضات السوقية",
  "أعلى وأفضل استخدام",
  "تسلسل القيمة العادلة",
  "مدخلات يمكن ملاحظتها",
  "تحليل الحساسية",
];

const sampleAssumptions = [
  "استمرار الطلب بنفس المعدلات الحالية لمدة 5 سنوات",
  "عدم وجود تغييرات تنظيمية مؤثرة",
  "توفر تمويل عقاري بشروط مستقرة",
];

export function App() {
  const [fileName, setFileName] = useState<string>("");
  const [reportText, setReportText] = useState<string>("");

  const checklist = useMemo<ChecklistItem[]>(() => {
    const source = reportText.toLowerCase();
    const rows: ChecklistItem[] = [];

    for (const item of ivsElements) {
      rows.push({ name: item, found: source.includes(item.toLowerCase()), standard: "IVS" });
    }

    for (const item of ifrs13Elements) {
      rows.push({ name: item, found: source.includes(item.toLowerCase()), standard: "IFRS 13" });
    }

    return rows;
  }, [reportText]);

  const missing = checklist.filter((x) => !x.found);
  const matched = checklist.filter((x) => x.found).length;
  const confidence = Math.round((matched / checklist.length) * 100) || 0;

  const riskLevel = confidence >= 80 ? "منخفض" : confidence >= 50 ? "متوسط" : "مرتفع";

  const unsupportedAssumptions = sampleAssumptions.filter((assumption) => {
    const firstWord = assumption.split(" ")[0];
    return firstWord && !reportText.includes(firstWord);
  });

  const exportSummary = () => {
    const content = [
      "ملخص مراجعة التقييم",
      `الملف: ${fileName || "غير محدد"}`,
      `نسبة الاكتمال: ${confidence}%`,
      `مؤشر المخاطر: ${riskLevel}`,
      "",
      "العناصر الناقصة:",
      ...missing.map((item) => `- ${item.standard}: ${item.name}`),
      "",
      "الافتراضات غير المدعومة:",
      ...unsupportedAssumptions.map((item) => `- ${item}`),
    ].join("\n");

    const blob = new Blob([content], {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "review-summary.doc";
    link.click();
    URL.revokeObjectURL(link.href);
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-100 to-white p-4 sm:p-8" dir="rtl">
      <section className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl bg-white p-6 shadow-sm">
          <h1 className="text-2xl font-bold text-slate-900">مساعد مراجعة تقارير التقييم العقاري</h1>
          <p className="mt-2 text-sm text-slate-600">
            نموذج أولي عملي لمراجعة تقارير التقييم في السوق السعودي وفق IVS و IFRS 13.
          </p>
        </header>

        <section className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">1) رفع التقرير</h2>
            <input
              type="file"
              accept="application/pdf"
              className="block w-full rounded-xl border border-slate-300 p-3 text-sm"
              onChange={(e) => setFileName(e.target.files?.[0]?.name ?? "")}
            />
            <p className="mt-2 text-xs text-slate-500">الملف المختار: {fileName || "لا يوجد"}</p>

            <label className="mt-4 block text-sm font-medium">نص مستخرج من التقرير (محاكاة للنموذج الأولي)</label>
            <textarea
              className="mt-2 h-48 w-full rounded-xl border border-slate-300 p-3 text-sm"
              placeholder="الصق النص المستخرج من ملف PDF هنا..."
              value={reportText}
              onChange={(e) => setReportText(e.target.value)}
            />
          </div>

          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">2) المؤشرات</h2>
            <div className="grid grid-cols-2 gap-3 text-center">
              <div className="rounded-xl bg-slate-100 p-4">
                <p className="text-xs text-slate-500">الثقة</p>
                <p className="text-2xl font-bold">{confidence}%</p>
              </div>
              <div className="rounded-xl bg-slate-100 p-4">
                <p className="text-xs text-slate-500">المخاطر</p>
                <p className="text-2xl font-bold">{riskLevel}</p>
              </div>
            </div>

            <h3 className="mt-5 text-sm font-semibold">افتراضات غير مدعومة</h3>
            <ul className="mt-2 space-y-2 text-sm">
              {unsupportedAssumptions.length === 0 ? (
                <li className="rounded-lg bg-emerald-50 p-2 text-emerald-700">لا توجد ملاحظات حرجة.</li>
              ) : (
                unsupportedAssumptions.map((item) => (
                  <li key={item} className="rounded-lg bg-amber-50 p-2 text-amber-700">
                    {item}
                  </li>
                ))
              )}
            </ul>
          </div>
        </section>

        <section className="rounded-2xl bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">3) قائمة المراجع</h2>
            <button
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
              onClick={exportSummary}
            >
              تصدير الملخص إلى Word
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                <tr className="bg-slate-100 text-right">
                  <th className="p-2">المعيار</th>
                  <th className="p-2">العنصر</th>
                  <th className="p-2">الحالة</th>
                </tr>
              </thead>
              <tbody>
                {checklist.map((item) => (
                  <tr key={`${item.standard}-${item.name}`} className="border-t border-slate-200">
                    <td className="p-2">{item.standard}</td>
                    <td className="p-2">{item.name}</td>
                    <td className="p-2">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-medium ${
                          item.found ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
                        }`}
                      >
                        {item.found ? "موجود" : "ناقص"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}
