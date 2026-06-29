# Realtime Speaker Translator

Local Windows MVP for translating incoming audio from another app. It listens to the selected speaker/output device through Windows loopback, transcribes speech, translates it, and shows the result in a local web UI.

The app can also generate answer suggestions using either a local file-based knowledge base or general AI advice.

## Features

- Captures speaker/output audio, not microphone input.
- Shows original transcript and translation in near real time.
- Supports RAG-style suggestions from local files.
- Supports general AI suggestions without a knowledge base.
- Logs each session transcript with original text and translation.
- Lets you clear Conversation and Suggestions in the UI.
- Lets you choose the suggestions language in the UI.

## Quick Start

1. Copy `.env.example` to `.env`.
2. Fill in `OPENAI_API_KEY` in `.env`.
3. Adjust language settings if needed:
   - `SOURCE_LANGUAGE=auto`
   - `TARGET_LANGUAGE=ru`
   - `SUGGESTIONS_LANGUAGE=target`
4. Run `START.bat`.
5. Open `http://127.0.0.1:8787`.
6. Click `Start` in the web UI.

The first launch creates `.venv` and installs dependencies from `requirements.txt`.

## Speaker Selection

List available speakers and loopback devices:

```powershell
.venv\Scripts\python.exe -m realtime_translator devices
```

By default, the app listens to the Windows default speaker. To listen to a specific output device, put part of its name into `.env`:

```env
SPEAKER_NAME=Razer
```

The app you want to translate must output audio to the same speaker/output device.

## Knowledge Base Suggestions

Enable RAG suggestions:

```env
ENABLE_RAG_SUGGESTIONS=true
KNOWLEDGE_BASE_PATH=knowledge_base
```

Put `.txt`, `.md`, `.json`, or `.csv` files into `knowledge_base`. The app searches these files and asks AI to generate concise suggestions from the relevant snippets.

`knowledge_base/` is ignored by git by default so private company data is not published.

## General AI Advice

Enable general suggestions without a knowledge base:

```env
ENABLE_GENERAL_ADVICE=true
```

You can enable both RAG suggestions and general advice at the same time.

## Latency And Accuracy

Main tuning settings:

```env
CHUNK_SECONDS=2.0
AUDIO_OVERLAP_SECONDS=0.6
SILENCE_RMS_THRESHOLD=0.004
AUDIO_QUEUE_MAX_CHUNKS=3
STT_MODEL=gpt-4o-transcribe
STT_PROMPT=
```

`CHUNK_SECONDS` controls how much audio is sent per transcription request. Smaller values reduce latency but may reduce transcription quality. `AUDIO_OVERLAP_SECONDS` helps avoid losing words at chunk boundaries. `SILENCE_RMS_THRESHOLD` controls silence filtering. `AUDIO_QUEUE_MAX_CHUNKS` limits backlog so old audio does not build up into high latency. `STT_PROMPT` can improve recognition of names, product terms, acronyms, and domain-specific vocabulary.

For better recognition, set the source language explicitly when you know it:

```env
SOURCE_LANGUAGE=en
```

## Transcript Logs

Each `Start` session can create a transcript log:

```env
ENABLE_TRANSCRIPT_LOG=true
TRANSCRIPT_LOG_DIR=logs/transcripts
```

Logs contain original text and translation. `logs/` is ignored by git.

## Security Notes

- Do not commit `.env`.
- Do not commit `knowledge_base/`.
- Do not commit `logs/`.
- Keep `APP_HOST=127.0.0.1` unless you intentionally want LAN access.

## Current Limitations

- This is near-realtime chunk-based processing, not true low-latency streaming STT.
- It captures all audio from the selected output device, not just one application.
- The current provider implementation uses OpenAI/OpenAI-compatible APIs.
- For production-grade latency, a streaming STT API and stronger audio/VAD pipeline are recommended.

---

# Realtime Speaker Translator

Локальный Windows MVP для перевода входящего аудио из другого приложения. Программа слушает выбранный динамик/output-устройство через Windows loopback, распознает речь, переводит ее и показывает результат в локальном web-интерфейсе.

Также приложение умеет генерировать подсказки для ответа: через локальную файловую базу знаний или через обычные AI-советы.

## Возможности

- Захватывает звук динамика/output-устройства, а не микрофон.
- Показывает оригинальный текст и перевод почти в реальном времени.
- Поддерживает RAG-подсказки из локальных файлов.
- Поддерживает общие AI-подсказки без базы знаний.
- Логирует каждую сессию: оригинал и перевод.
- Позволяет очищать Conversation и Suggestions в интерфейсе.
- Позволяет выбрать язык подсказок в интерфейсе.

## Быстрый старт

1. Скопируйте `.env.example` в `.env`.
2. Заполните `OPENAI_API_KEY` в `.env`.
3. При необходимости поменяйте языки:
   - `SOURCE_LANGUAGE=auto`
   - `TARGET_LANGUAGE=ru`
   - `SUGGESTIONS_LANGUAGE=target`
4. Запустите `START.bat`.
5. Откройте `http://127.0.0.1:8787`.
6. Нажмите `Start` в web-интерфейсе.

Первый запуск создаст `.venv` и установит зависимости из `requirements.txt`.

## Выбор динамика

Показать доступные speakers и loopback devices:

```powershell
.venv\Scripts\python.exe -m realtime_translator devices
```

По умолчанию приложение слушает системный динамик Windows. Чтобы слушать конкретное output-устройство, укажите часть его имени в `.env`:

```env
SPEAKER_NAME=Razer
```

Приложение, которое вы переводите, должно выводить звук именно в этот динамик/output-устройство.

## Подсказки из базы знаний

Включить RAG-подсказки:

```env
ENABLE_RAG_SUGGESTIONS=true
KNOWLEDGE_BASE_PATH=knowledge_base
```

Положите `.txt`, `.md`, `.json` или `.csv` файлы в `knowledge_base`. Приложение найдет релевантные фрагменты и попросит AI сформировать короткие подсказки.

`knowledge_base/` по умолчанию добавлен в `.gitignore`, чтобы приватные данные компании не публиковались.

## Общие AI-советы

Включить общие подсказки без базы знаний:

```env
ENABLE_GENERAL_ADVICE=true
```

Можно включить RAG-подсказки и общие AI-советы одновременно.

## Задержка и точность

Основные настройки:

```env
CHUNK_SECONDS=2.0
AUDIO_OVERLAP_SECONDS=0.6
SILENCE_RMS_THRESHOLD=0.004
AUDIO_QUEUE_MAX_CHUNKS=3
STT_MODEL=gpt-4o-transcribe
STT_PROMPT=
```

`CHUNK_SECONDS` управляет размером аудио-куска для распознавания. Меньшее значение снижает задержку, но может ухудшить качество распознавания. `AUDIO_OVERLAP_SECONDS` помогает не терять слова на границах кусков. `SILENCE_RMS_THRESHOLD` управляет фильтрацией тишины. `AUDIO_QUEUE_MAX_CHUNKS` ограничивает очередь, чтобы старые куски не накапливались в большую задержку. `STT_PROMPT` можно использовать для имен, продуктов, аббревиатур и терминов предметной области.

Если язык разговора известен, лучше указать его явно:

```env
SOURCE_LANGUAGE=en
```

## Логи транскриптов

Каждая сессия `Start` может создавать transcript-log:

```env
ENABLE_TRANSCRIPT_LOG=true
TRANSCRIPT_LOG_DIR=logs/transcripts
```

В лог пишутся оригинальный текст и перевод. `logs/` добавлен в `.gitignore`.

## Безопасность

- Не коммитьте `.env`.
- Не коммитьте `knowledge_base/`.
- Не коммитьте `logs/`.
- Оставляйте `APP_HOST=127.0.0.1`, если не хотите открывать доступ из локальной сети.

## Текущие ограничения

- Это near-realtime обработка по кускам аудио, а не настоящий low-latency streaming STT.
- Захватывается весь звук выбранного output-устройства, а не только одно приложение.
- Сейчас реализован OpenAI/OpenAI-compatible provider.
- Для production-level задержки лучше переходить на streaming STT API и более сильный audio/VAD pipeline.
