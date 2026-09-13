# مشروع Status — توثيق شامل للمتابعة

هذا الملف يلخّص كل شي صار بمشروع "Status" (تصحيح بيانات القوانين بملف JLexAI) من أول خطوة لآخر خطوة، عشان تقدر تكمل الشغل من مكان/محادثة تانية بدون ما تحتاج تعيد شرح أي شي.

المجلد الرئيسي على جهازك: `C:\Users\user\Desktop\status\` — كل ملفات الـ .py المذكورة هون موجودة فيه مباشرة (بنية مسطّحة، بدون مجلدات فرعية للكود).

---

## 1. المشكلة الأصلية

ملف `RefLaws_merged_20260907_132256.json` (قوانين + تعديلاتها المتداخلة جوا `Mod_Legs`) فيه:
- **4,315 سجل قانون إجمالي** (top-level + متداخل)
- **2,761 سجل** منها كان **ناقص مفتاح `Status` بالكامل** (مو بس فاضي — غير موجود إطلاقًا بالـ JSON)

---

## 2. خط الأنابيب (Pipeline) — Phase 1 إلى 3

### Phase 1 — `insert_missing_status.py`
- يضيف مفتاح `Status` بقيمة فارغة `""` للسجلات الناقصة، **بالموقع الصحيح** ضمن كل سجل (متعلّم من قالب مرجعي موجود بنفس الملف — top-level وnested كل وحدة إلها قالبها لحالها)، بدون ما يلمس أي سجل عنده `Status` أصلاً ولا أي حقل تاني.
- يكتب نسخة جديدة (الأصل ما بينلمس أبدًا) بمجلد `outputs\` باسم `RefLaws_merged_status_filled_<timestamp>.json`.
- Log كامل بمجلد `logs\`.

### Phase 2 — `enrich_status_from_reference.py`
- يعبّي قيم `Status` الفارغة بمطابقة `URL` (كمفتاح فريد) مع ملف مرجعي: `RefLaws_v07_CorrMeta\RefLaws_v07_CorrMeta.json`.
- **مشكلة اتصلحت:** الملف المرجعي كان فيه BOM (UTF-8 with BOM) — الحل: قراءة بـ `encoding="utf-8-sig"` بدل `"utf-8"` بكل مكان.
- ~246-257 سجل بدون URL أصلاً (قوانين مضافة حديثًا) ما انطابقوا — هدول محتاجين طريقة تانية (يدوية، عن طريق البورتالات لاحقًا).
- يكتشف تلقائيًا آخر ملف `RefLaws_merged_status_*.json` بمجلد `outputs\`.

### Phase 3 — `export_zero_articles_and_empty_status.py`
- يصدّر ملفين تشخيصيين (سجلات كاملة كما هي، بدون تعديل):
  - `laws_zero_articles_<timestamp>.json` — **13 سجل** عدد موادها صفر مؤكد (لازم `Article_Count` **و** طول `Base_Articles`+`Reflected_Articles` يتطابقوا على صفر سوا، وإلا بينسجل تعارض بالـ log بدون ما يخمّن).
  - `laws_empty_status_<timestamp>.json` — **257 سجل** الـ `Status` تبعها لسا فاضي.

---

## 3. البورتالات (Phase 4) — واجهات المتطوعين

### البنية المشتركة
| ملف | الوظيفة |
|---|---|
| `config.py` | كل الإعدادات المركزية (مسارات، أسماء Sheets، أعمدة، أسماء المتطوعين) — يقرأ الأسرار من `.env` عبر `os.environ` |
| `gsheets_client.py` | طبقة وصول عامة لـ Google Sheets (فتح/قراءة/كتابة/upsert)، بدون معرفة بأي schema محدد |
| `ui_theme.py` | هوية بصرية موحّدة (خط Tajawal، ألوان، كروت، أزرار، RTL كامل) تستوردها الأربع واجهات كلهم |
| `cloud_secrets.py` | يجسر بين أسرار Streamlit Cloud (`st.secrets`) ونفس متغيرات البيئة يلي `config.py` بيقرأها من `.env` محليًا — بدون ما يغيّر `config.py` نفسه إطلاقًا |
| `show_service_account_email.py` | يطبع إيميل الـ Service Account (من ملف الـ JSON) عشان تشاركه مع الشيتات |
| `generate_password_hash.py` | يولّد bcrypt hash لأي كلمة سر (تحطها بـ `.env`) |
| `push_initial_data_to_sheets.py` | سكربت تشغيل مرة وحدة: يعبّي الشيتين من ملفي Phase 3 (**تحذير: يمسح ويعيد الكتابة، لا تشغله بعد ما يبلش المتطوعين**) |

### البورتال الأول — القوانين بدون مواد (13 سجل، متطوع واحد)
- `portal1_data.py` — طبقة بيانات: تاب `progress` (13 صف، حالة الإنجاز) وتاب `articles` (سطر لكل مادة يضيفها المتطوع).
- `portal1_volunteer_app.py` — تسجيل دخول بكلمة سر وحدة، عرض القوانين، فتح أي وحدة لإضافة مواد (رقم يتزايد تلقائيًا + نص)، تعليم كمكتمل.
- `portal1_admin_app.py` — متابعة تقدّم Read-only.
- كل مادة تُخزّن كـ `{"article_number": int, "text": str}` بالملف النهائي — **افتراض غير مؤكد 100%** (ما شفنا مثال حقيقي بالبيانات الأصلية لمادة معبّاة)، سهل التعديل بسطر وحد بـ `merge_portal1_articles.py` لو الأسماء مختلفة عندك.

### البورتال الثاني — القوانين بدون Status (257 سجل، 5 متطوعين)
- `portal2_data.py` — كل متطوع (v1 إلى v5) إله تاب Google Sheet معزول تمامًا (بدون تداخل صفوف بين حد وحد). أعمدة الشيت مُشتقّة ديناميكيًا من البيانات نفسها (union كل المفاتيح، ما عدا `Base_Articles`/`Mod_Legs`/`Reflected_Articles` المستثناة من الشيت أصلاً).
- `portal2_volunteer_app.py`:
  - تسجيل دخول: اختيار حساب (v1-v5) ← أول مرة بس يكتب اسمه الحقيقي (بينحفظ بتاب صغير `_volunteer_names` وما بينسأل تاني) ← كلمة سر مشتركة.
  - قائمة منسدلة (dropdown) وحدة لاختيار القانون — **الاسم المعروض هو `Leg_Name` بالضبط بدون أي إضافة** (عشان المتطوع ينسخه للبحث الخارجي)، مع صندوق `st.code()` مخصص للنسخ الآمن.
  - تفتح تلقائيًا على أول قانون (مش شاشة فاضية).
  - كل حقل فاضي إله كارد مستقل، مرتبين منطقيًا (رقم التشريع+السنة جنب بعض، تنبيه بأهم 3 حقول: الحالة/تاريخ الإصدار/تاريخ الانتهاء).
  - **الحالة (`Status`) اختيار إجباري بس: "ساري" أو "غير ساري"** — مو نص حر.
  - بيعبّي **بس** الحقول الفاضية فعليًا، بدون ما يلمس أي حقل معبّى أصلاً.
- `portal2_admin_app.py` — تقدّم إجمالي + لكل متطوع لحاله + قائمة المتبقي.

### مشاكل حقيقية اتصلحت بالتصميم (مهم تعرفها لو بدك تعدّل لاحقًا)
1. **زرار Streamlit بلا حدود ولا خلفية** بعد إزالة `border: none` بدون بديل — انصلح بإعطاء لون خلفية وحدّ صريح لكل حالة (عادي/primary/hover).
2. **`PORTAL2_EXCLUDED_FROM_FORM` كانت تُستخدم لغرضين مختلفين بالغلط** (استثناء من التعديل + استثناء من الشيت بالكامل) → `Leg_Name` طلع مفقود كليًا من شيتات المتطوعين. انصلحت بفصلها لـ `PORTAL2_EXCLUDED_FROM_SHEET` و`PORTAL2_EXCLUDED_FROM_EDITING`.
3. **Streamlit selectbox بيضيع تتبّع الاختيار عبر الصفحات** لما يكون في خيارين نصهم المعروض متطابق بالضبط (وهذا صار فعليًا لأنه في قوانين بنفس الاسم بالضبط) — انصلحت بإضافة مسافة غير مرئية (`\u200b`) للتكرارات الداخلية فقط، بدون ما يأثر على المعروض ولا على صندوق النسخ.
4. **`requirements.txt` كان فيه `torch==2.11.0+cu128`** (نتيجة `pip freeze` من venv فيه مشروع تاني) — سبب فشل نشر Streamlit Cloud بالكامل. الصح: بس `streamlit`, `gspread`, `google-auth`, `python-dotenv`, `bcrypt`.
5. **ملفات JSON ضخمة (>100MB) انضافت لأول commit بالغلط** لأنه `.gitignore` ما كان مستثني `outputs\` وملفات الداتا الكبيرة بجذر المشروع من البداية. الحل كان `git rm --cached` + `git commit --amend` (مو commit جديد، عشان ما يضل التاريخ القديم فيه الملفات الضخمة).
6. **TOML وSecrets:** لازم علامات اقتباس ثلاثية مفردة `'''` (literal string) حول محتوى JSON الخاص بالـ service account على Streamlit Cloud، مش `"""` — لأنه `"""` بتفسّر `\n` كسطر جديد فعلي وتكسر الـ JSON. الاسم المستخدم بالسحابة: `GOOGLE_SERVICE_ACCOUNT_FILE_CONTENT` (محتوى كامل، مش مسار).

---

## 4. الدمج النهائي (رجوع للملف الكبير)

- `merge_common.py` — منطق مشترك: يمشي recursively على كل الملف (top-level + متداخل) ويطابق بمفتاح مركّب `(Leg_Name, Leg_Number, Year)`. **لو التطابق صفر أو أكثر من واحد، بيتجاهل السجل ويسجّله بالـ log كـ "يحتاج مراجعة يدوية" — ما بيخمّن أبدًا.**
- **ترتيب التشغيل الإجباري:**
  ```
  python merge_portal1_articles.py
  python merge_portal2_status.py
  ```
  الثاني بيلتقط تلقائيًا ناتج الأول (مو الملف الأصلي قبل الدمج)، عشان الملف النهائي يجمع إصلاح المواد + الحالة سوا. الناتج: `RefLaws_merged_final_<timestamp>.json`.

---

## 5. حالة Google Sheets والنشر حاليًا

- **Service Account:** `status@lawauditnicst.iam.gserviceaccount.com` (مشروع Google Cloud: `lawauditnicst`) — تحت نفس المشروع يلي فيه شيت `adding_articles` القديم، بس Service Account جديد مخصص لهاد الشغل.
  - تذكير أمان: المفتاح الخاص (private key) تبع هاد الحساب انلصق بالمحادثة كنص صريح بمرحلة سابقة. لو لسا ما رجّعته (Add Key جديد + حذف القديم بـ IAM & Admin > Service Accounts)، هاي خطوة لسا معلّقة وينصح تسويها.
- **الشيتات (منشأة يدويًا من طرفك، مو من الكود):**
  - `status_portal_zero_articles` — ID: `1-FM6XdWGTZM8I7Lb-48WJ9BX5OTj8dcsWl6TlJZK8m4`
  - `status_portal_empty_status` — ID: `1UaAEDdguR1-5ntwsGvk5ZklUTVzSoP_wt0UxFpslqE8`
  - الكود **لا ينشئ شيتات جديدة أبدًا** (Service Account بلا مساحة Drive خاصة، بينهار بخطأ `storageQuotaExceeded`) — بس يفتح شيتات موجودة مسبقًا ومشارَكة معه.
- **GitHub:** مستودع `AhmedMJarrah/status-portals` — بعد تصحيح مشكلة الملفات الضخمة، الـ push المفروض يشتغل. لسا ما تأكدنا من نجاح push نهائي بعد كل التعديلات الأخيرة.
- **Streamlit Community Cloud:** لسا مرحلة الإعداد — `requirements.txt` انصلح، والـ Secrets (TOML) جاهزة الصيغة الصحيحة لكل تطبيق من الأربعة.
- **لسا ولا متطوع دخل بيانات حقيقية** — كل الاختبارات لتاريخه كانت dry-run على بيانات فاضية.

---

## 6. أشياء لسا معلّقة / تحتاج قرار منك

1. تأكيد المعنى الدقيق لـ `Replaced_For` و`Replaced_By` — حطيت افتراض بالتسميات المعروضة بواجهة البورتال الثاني، لسا ما تأكدلي إذا صح.
2. تأكيد صيغة `article_number`/`text` بملف الدمج النهائي لبورتال 1 (نقطة الافتراض بقسم 3 فوق).
3. تدوير مفتاح الـ Service Account (أمان، مو إجباري تقني).
4. إكمال نشر الأربع تطبيقات فعليًا على Streamlit Cloud والتأكد من عملهم بالسحابة (لسا ما تم تأكيد ذلك).
5. تشغيل `push_initial_data_to_sheets.py` مرة وحدة أخيرة (بعد أي تعديل على الأعمدة) قبل ما المتطوعين يبلشوا فعليًا.

---

## 7. قائمة كل ملفات .py بالمشروع (بالترتيب الزمني لإنشائها)

```
tst.py, verify_status.py                          ← تشخيص أصلي (منك)
insert_missing_status.py                          ← Phase 1
enrich_status_from_reference.py                   ← Phase 2
export_zero_articles_and_empty_status.py          ← Phase 3
config.py                                         ← إعدادات مركزية (البورتالات)
gsheets_client.py                                 ← طبقة Sheets العامة
push_initial_data_to_sheets.py                    ← تعبئة أولية للشيتات
show_service_account_email.py                     ← أداة مساعدة صغيرة
generate_password_hash.py                         ← أداة مساعدة صغيرة
ui_theme.py                                       ← تصميم مشترك
portal1_data.py, portal1_volunteer_app.py, portal1_admin_app.py
portal2_data.py, portal2_volunteer_app.py, portal2_admin_app.py
cloud_secrets.py                                  ← جسر Streamlit Cloud
merge_common.py, merge_portal1_articles.py, merge_portal2_status.py
```
