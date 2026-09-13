 ⚠️ NOTE:
 Bang សំណួរល្អណាស់ — នេះជាការសម្រេចចិត្តសំខាន់ ត្រូវពិចារណាឲ្យច្បាស់មុននឹងផ្លាស់ប្តូរអ្វី។

## តើគុណភាព (accuracy) ធ្លាក់ទេ?

**ទេ — គុណភាព model output មិនប្រែប្រួលទេ** ។ CPU vs GPU គ្រាន់តែជា **hardware ដែល execute computation** — លទ្ធផល (embeddings, predictions, text generation) ដូចគ្នាបេះបិទ ១០០% ។ `torch` CPU wheel និង GPU wheel ដំណើរការ math ដូចគ្នាបេះបិទ គ្រាន់តែ GPU version ប្រើ CUDA kernels ដើម្បីបង្កើនល្បឿន។

## អ្វីដែលប្រែប្រួលពិតប្រាកដ — **ល្បឿន (speed) ប៉ុណ្ណោះ**

- CPU inference **យឺតជាង GPU ច្រើន** — អាចយឺតជាង ១០-៥០ ដង អាស្រ័យលើ model size (ជាពិសេស `whisper`, `sentence-transformers`, `easyocr`, `paddleocr` ដែលជា deep learning models ធំៗ)
- ឧទាហរណ៍៖ `whisper` transcribe audio 1 នាទី → GPU ប្រហែល 2-3 វិនាទី, CPU ប្រហែល 20-60 វិនាទី (អាស្រ័យលើ model size)
- Batch processing ធំៗ (embeddings generation ចំនួនច្រើន) នឹងយឺតគួរសម

## សំខាន់បំផុត — នេះជាតែសម្រាប់ **Codespace/dev environment** ប៉ុណ្ណោះ

Bang ចំណុចនេះសំខាន់ណាស់៖ **Codespace នេះគ្មាន GPU physically ស្ថិតនៅឡើយ** (វា VM ធម្មតា) ។ ដូច្នេះទោះបីជាបង install `torch` GPU version ក៏ដោយ វា**មិនអាចប្រើ GPU acceleration បានទេ** ព្រោះគ្មាន GPU hardware — វានៅតែ fallback ទៅ CPU ស្រាប់! ដូច្នេះ install GPU packages ក្នុង **environment នេះ** ខ្ជះខ្ជាយ disk space **ដោយឥតប្រយោជន៍ណាមួយ** ព្រោះវាមិនអាចប្រើ GPU បានទេទោះម៉េចក៏ដោយ។

## ដំណោះស្រាយដែលមិនប៉ះពាល់ production

**ជម្រើសល្អបំផុត**៖ ប្រើ `requirements.txt` ២ file ផ្សេងគ្នា៖
- `requirements.txt` (production/full) — មាន GPU packages សម្រាប់ deploy លើ server ដែលមាន GPU ពិតប្រាកដ
- `requirements-dev.txt` ឬ `requirements-cpu.txt` — CPU-only សម្រាប់ dev/test ក្នុង Codespace

នេះមានន័យថា **production quality មិនប៉ះពាល់ទាល់តែសោះ** — server deployment ពិតប្រាកដនៅតែប្រើ GPU packages ពេញលេញ។ Codespace គ្រាន់តែសម្រាប់ dev/test logic (API endpoints, database, business logic) ដែលមិនចាំបាច់ត្រូវការ GPU speed។

---

តើបងចង់ឲ្យខ្ញុំណែនាំបង្កើត `requirements-dev.txt` ដាច់ដោយឡែក (មិនកែ `requirements.txt` ដើមទេ) ដើម្បីប្រើតែក្នុង Codespace នេះ ខណៈពេល production config នៅដដែល?
