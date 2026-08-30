export interface TranscriptionResult {
  success: boolean;
  text: string;
  model: string;
  durationMs: number;
  error?: string;
}

export interface TranscribeOptions {
  audioBase64: string;
  mimeType?: string;
  filename?: string;
  prompt?: string;
  language?: string;
}

const DEFAULT_FOOD_PROMPT =
  'Food ordering intent, Indian restaurant names and dishes: biryani, pizza, iced latte, cold coffee, burger, pasta, dosa, momos, garlic bread, fries, Domino\'s Pizza, Subway, Starbucks, Third Wave Coffee, Blue Tokai, Truffles, Meghana Foods, Haldiram\'s, KFC, Burger King, Swiggy.';

export class WhisperTranscriber {
  /**
   * Transcribes base64-encoded audio using Groq's ultra-fast Whisper Large v3 model.
   */
  public static async transcribe(options: TranscribeOptions): Promise<TranscriptionResult> {
    const startTime = Date.now();
    const apiKey = process.env.GROQ_API_KEY;

    if (!apiKey) {
      return {
        success: false,
        text: '',
        model: 'none',
        durationMs: Date.now() - startTime,
        error: 'GROQ_API_KEY is not configured in backend environment.',
      };
    }

    if (!options.audioBase64 || typeof options.audioBase64 !== 'string') {
      return {
        success: false,
        text: '',
        model: 'none',
        durationMs: Date.now() - startTime,
        error: 'Invalid or missing audio payload (audioBase64 is required).',
      };
    }

    try {
      // Strip any data URI prefix if present (e.g. data:audio/m4a;base64,...)
      const base64Data = options.audioBase64.replace(/^data:[^;]+;base64,/, '').trim();
      const audioBuffer = Buffer.from(base64Data, 'base64');

      if (audioBuffer.length === 0) {
        return {
          success: false,
          text: '',
          model: 'none',
          durationMs: Date.now() - startTime,
          error: 'Decoded audio buffer is empty.',
        };
      }

      // Determine appropriate mime type and extension
      const mimeType = options.mimeType || 'audio/m4a';
      let extension = 'm4a';
      if (mimeType.includes('webm')) extension = 'webm';
      else if (mimeType.includes('mp4')) extension = 'mp4';
      else if (mimeType.includes('wav')) extension = 'wav';
      else if (mimeType.includes('ogg') || mimeType.includes('opus')) extension = 'ogg';
      else if (mimeType.includes('mpeg') || mimeType.includes('mp3')) extension = 'mp3';

      const filename = options.filename || `recording.${extension}`;

      // Construct native FormData with Blob for Groq OpenAI-compatible audio API
      const formData = new FormData();
      const blob = new Blob([new Uint8Array(audioBuffer)], { type: mimeType });
      (formData as any).append('file', blob, filename);
      formData.append('model', 'whisper-large-v3');
      formData.append('response_format', 'json');
      formData.append('temperature', '0.0');

      const domainPrompt = options.prompt || DEFAULT_FOOD_PROMPT;
      formData.append('prompt', domainPrompt);

      if (options.language) {
        formData.append('language', options.language);
      }

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 20000); // 20s timeout

      const response = await fetch('https://api.groq.com/openai/v1/audio/transcriptions', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${apiKey}`,
        },
        body: formData,
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (!response.ok) {
        const errText = await response.text();
        console.error('Groq Whisper API error:', response.status, errText);
        return {
          success: false,
          text: '',
          model: 'whisper-large-v3',
          durationMs: Date.now() - startTime,
          error: `Groq Whisper API responded with HTTP ${response.status}: ${errText}`,
        };
      }

      const result = (await response.json()) as { text?: string };
      const transcribedText = (result.text || '').trim();

      return {
        success: true,
        text: transcribedText,
        model: 'whisper-large-v3',
        durationMs: Date.now() - startTime,
      };
    } catch (err: any) {
      console.error('Whisper transcription exception:', err);
      return {
        success: false,
        text: '',
        model: 'whisper-large-v3',
        durationMs: Date.now() - startTime,
        error: err.name === 'AbortError' ? 'Transcription request timed out after 20s.' : err.message,
      };
    }
  }
}
