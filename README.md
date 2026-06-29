# Realtime Speaker Translator

Локальный MVP для перевода входящего аудиопотока из приложения: программа слушает не микрофон, а звук выбранного динамика через Windows loopback, распознает речь, переводит ее и показывает результат в web-интерфейсе.

## Быстрый старт

1. Откройте `.env` и заполните `OPENAI_API_KEY`.
2. При необходимости поменяйте:
   - `SOURCE_LANGUAGE=auto`
   - `TARGET_LANGUAGE=ru`
   - `SPEAKER_NAME=` оставьте пустым для системного динамика по умолчанию.
3. Запустите `START.bat`.
4. Откройте `http://127.0.0.1:8787`.
5. Нажмите `Start` в интерфейсе.

Первый запуск создаст `.venv` и установит зависимости из `requirements.txt`.

## Выбор динамика

Команда:

```powershell
.venv\Scripts\python.exe -m realtime_translator devices
```

Покажет доступные speakers и loopback devices. Если нужно слушать не динамик по умолчанию, скопируйте часть имени в `SPEAKER_NAME`.

Важно: приложение, которое вы переводите, должно выводить звук именно в этот динамик/наушники.

## Подсказки

RAG по базе знаний:

```env
ENABLE_RAG_SUGGESTIONS=true
KNOWLEDGE_BASE_PATH=knowledge_base
```

Сложите `.txt`, `.md`, `.json` или `.csv` файлы в папку `knowledge_base`. В UI можно нажать `Refresh KB`.

Общие AI-советы без базы знаний:

```env
ENABLE_GENERAL_ADVICE=true
```

Можно включить оба режима одновременно.

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

`CHUNK_SECONDS` уменьшает задержку, но слишком маленькое значение ухудшает распознавание. `AUDIO_OVERLAP_SECONDS` помогает не терять слова на границах кусков. Если тихая речь пропадает, уменьшите `SILENCE_RMS_THRESHOLD`. `AUDIO_QUEUE_MAX_CHUNKS` ограничивает очередь аудио, чтобы старые куски не копились в задержку. `STT_PROMPT` можно использовать для терминов, имен продуктов и специфики разговора.

## Ограничения MVP

- Это near-realtime по кускам аудио, а не нативный low-latency streaming.
- Захватывается весь звук выбранного output-устройства, а не только одно приложение.
- Сейчас реализован OpenAI-провайдер; другие STT API можно добавить в `realtime_translator/ai.py`.
