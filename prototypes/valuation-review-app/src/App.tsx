import { ChangeEvent, useMemo, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker;

type RiskLevel = 'مرتفع' | 'متوسط' | 'منخفض';

type ChecklistItem = {
  id: string;
  label: string;
  completed: boolean;
};

type Flag = {
  title: string;
  level: RiskLevel;
  note: string;
};

const ivsIfrsRequirements = [
  'تاريخ التقييم',
  'أساس القيمة (القيمة العادلة / السوقية)',
  'الغرض من التقييم',
  'الافتراضات الجوهرية',
  'قيود نطاق العمل',
  'مصدر بيانات السوق',
  'مستوى مدخلات IFRS 13 (Level 1/2/3)',
  'اختبارات الحساسية',
  'التحقق من الاستقلالية وتضارب المصالح'
];

const fakeExtractAssumptions = (text: string): string[] => {
  const dictionary = ['نسبة الإشغال', 'معدل الخصم', 'معدل النمو', 'سعر المتر', 'فترة التدفقات النقدية', 'العمر الاقتصادي المتبقي'];
  return dictionary.filter((item) => text.includes(item));
};

const riskFromMissing = (missingCount: number): RiskLevel => {
  if (missingCount >= 4) return 'مرتفع';
  if (missingCount >= 2) return 'متوسط';
  return 'منخفض';
};

async function extractPdfText(file: File): Promise<string> {
  const bytes = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: bytes }).promise;
  const pages: string[] = [];
  for (let pageIndex = 1; pageIndex <= pdf.numPages; pageIndex += 1) {
    const page = await pdf.getPage(pageIndex);
    const content = await page.getTextContent();
    const pageText = content.items
      .map((item) => ('str' in item ? item.str : ''))
      .join(' ')
      .trim();
    pages.push(pageText);
  }
  return pages.join('\n');
}

export default function App() {
  const [fileName, setFileName] = useState('');
  const [reportText, setReportText] = useState('');
  const [extractStatus, setExtractStatus] = useState('');
  const [extractError, setExtractError] = useState('');
  const [checklist, setChecklist] = useState<ChecklistItem[]>(ivsIfrsRequirements.map((item, index) => ({ id: String(index), label: item, completed: false })));

  const assumptions = useMemo(() => fakeExtractAssumptions(reportText), [reportText]);
  const missing = useMemo(() => checklist.filter((item) => !item.completed).map((item) => item.label), [checklist]);

  const flags = useMemo<Flag[]>(() => {
    const level = riskFromMissing(missing.length);
    const base: Flag[] = [{
      title: 'اكتمال متطلبات IVS / IFRS 13',
      level,
      note: level === 'مرتفع' ? 'يوجد نواقص مؤثرة قد تؤثر على الاعتمادية.' : level === 'متوسط' ? 'يوجد نواقص متوسطة وتحتاج استكمال قبل الاعتماد.' : 'الاستخدام مناسب مبدئيا مع مخاطر محدودة.'
    }];

    if (!assumptions.includes('معدل الخصم')) {
      base.push({ title: 'غياب معدل الخصم', level: 'مرتفع', note: 'تقييم التدفقات النقدية دون معدل خصم واضح يزيد عدم اليقين.' });
    }
    return base;
  }, [assumptions, missing.length]);

  const onFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setExtractError('');
    setExtractStatus('جاري استخراج النص من ملف PDF...');
    try {
      const text = await extractPdfText(file);
      setReportText(text);
      setExtractStatus(`تم استخراج النص بنجاح (${text.length} حرف).`);
    } catch {
      setExtractStatus('');
      setExtractError('تعذّر استخراج النص تلقائيا. يمكنك لصق النص يدويا في الحقل أدناه.');
    }
  };

  const onExportWord = () => {
    const content = `ملخص مراجعة تقييم عقاري\n\nاسم الملف: ${fileName || 'غير محدد'}\n\nالافتراضات المستخرجة:\n${assumptions.map((a) => `- ${a}`).join('\n')}\n\nالعناصر الناقصة:\n${missing.map((m) => `- ${m}`).join('\n')}\n\nإشارات المخاطر:\n${flags.map((f) => `- ${f.title}: ${f.level}`).join('\n')}\n`;

    const blob = new Blob([content], { type: 'application/msword' });
    const href = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = href;
    link.download = 'review-summary.doc';
    link.click();
    URL.revokeObjectURL(href);
  };

  return (
    <main className="min-h-screen bg-slate-100 p-4 text-slate-900" dir="rtl">
      <section className="mx-auto max-w-5xl space-y-4 rounded-xl bg-white p-6 shadow">
        <h1 className="text-2xl font-bold">مراجع تقييم عقاري (نموذج أولي)</h1>
        <p className="text-sm text-slate-600">واجهة عربية RTL لمراجعة التقارير بسرعة قبل الاعتماد النهائي.</p>

        <div className="rounded-lg border border-dashed border-slate-300 p-4">
          <label className="mb-2 block font-semibold">رفع تقرير التقييم (PDF)</label>
          <input type="file" accept="application/pdf" onChange={onFileChange} className="block w-full text-sm" />
          {fileName && <p className="mt-2 text-xs text-slate-500">تم اختيار: {fileName}</p>}
          {extractStatus && <p className="mt-2 text-xs text-emerald-700">{extractStatus}</p>}
          {extractError && <p className="mt-2 text-xs text-red-700">{extractError}</p>}
        </div>

        <div>
          <label className="mb-2 block font-semibold">نص التقرير المستخرج</label>
          <textarea value={reportText} onChange={(event) => setReportText(event.target.value)} rows={8} placeholder="سيظهر النص المستخرج من PDF هنا، أو يمكنك اللصق يدويا..." className="w-full rounded-lg border border-slate-300 p-3 text-sm" />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-slate-200 p-4"><h2 className="mb-2 font-bold">افتراضات رئيسية مستخرجة</h2><ul className="list-inside list-disc text-sm">{assumptions.length > 0 ? assumptions.map((a) => <li key={a}>{a}</li>) : <li>لا يوجد افتراضات مكتشفة بعد.</li>}</ul></div>
          <div className="rounded-lg border border-slate-200 p-4"><h2 className="mb-2 font-bold">قائمة التحقق IVS / IFRS 13</h2><div className="space-y-2 text-sm">{checklist.map((item) => (<label key={item.id} className="flex items-center gap-2"><input type="checkbox" checked={item.completed} onChange={() => setChecklist((prev) => prev.map((x) => (x.id === item.id ? { ...x, completed: !x.completed } : x)))} /><span>{item.label}</span></label>))}</div></div>
        </div>

        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4"><h2 className="mb-2 font-bold">إشارات المخاطر</h2><ul className="space-y-2 text-sm">{flags.map((flag, idx) => (<li key={idx}><strong>{flag.title}</strong> — مستوى الخطر: <span className="font-semibold">{flag.level}</span><p className="text-slate-700">{flag.note}</p></li>))}</ul></div>

        <button onClick={onExportWord} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700">تصدير ملخص المراجعة إلى Word</button>
      </section>
    </main>
  );
}
