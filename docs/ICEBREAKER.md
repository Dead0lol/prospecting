# Icebreaker Generator

The icebreaker generator creates personalized, authentic opening lines for cold outreach emails based on the lead's website content.

## Overview

Instead of sending generic "I love your website" messages, the icebreaker generator uses AI to analyze the actual content of each lead's website and generate specific, authentic compliments that reference real details from their site.

## How It Works

1. **Content Extraction**: During website crawling, we extract the full text content of each page
2. **AI Analysis**: The icebreaker generator sends this content (first 3000 chars) to OpenRouter AI
3. **Personalized Generation**: The AI writes a brief, specific compliment based on the actual website content
4. **Storage**: The icebreaker is stored in the `ice` column in Google Sheets

## Configuration

Add these settings to your `.env` file:

```bash
# Icebreaker generation
ICEBREAKER_TONE=professional and respectful
ICEBREAKER_LENGTH=2
```

### Configuration Options

**ICEBREAKER_TONE**
- Controls the tone and style of the generated icebreaker
- Examples:
  - `professional and respectful` - Formal, business-appropriate
  - `casual and friendly` - Relaxed, conversational
  - `enthusiastic and warm` - Energetic, positive
  - `direct and concise` - Straight to the point

**ICEBREAKER_LENGTH**
- Number of sentences to generate (1-3 recommended)
- `1` = Very brief (one sentence)
- `2` = Balanced (two sentences)
- `3` = More detailed (three sentences)

## Example Output

Given a fitness coach's website that emphasizes "science-based programming" and "flexible scheduling", the icebreaker might generate:

> "I noticed your emphasis on science-based programming tailored to individual body types—that's a refreshing approach in an industry full of cookie-cutter plans. The flexible scheduling you offer for busy professionals really shows you understand your clients' real-world constraints."

## When Icebreakers Are Generated

Icebreakers are generated:
- ✅ When OpenRouter API key is configured
- ✅ When website content is available and substantial (100+ characters)
- ✅ During the pipeline's classify_and_score phase

Icebreakers are skipped:
- ❌ When OpenRouter API key is not set
- ❌ When website content is too short or unavailable
- ❌ When API request fails (fails gracefully, leaves `ice` empty)

## API Usage

The icebreaker generator uses the same OpenRouter API key and model as the AI classifier:
- **API Key**: `OPENROUTER_API_KEY` from `.env`
- **Model**: `OPENROUTER_MODEL` from `.env`
- **Rate Limiting**: Respects `OPENROUTER_DELAY_SECONDS` between calls

## Prompting Strategy

The generator uses a carefully crafted prompt that:
1. Instructs the AI to be SPECIFIC (reference actual content)
2. Demands AUTHENTICITY (no generic praise)
3. Enforces BREVITY (configurable sentence count)
4. Prohibits sales pitch or questions
5. Focuses on unique approach, content, or value proposition

## Integration with Pipeline

The icebreaker generator is integrated into the main pipeline at `pipeline.py:classify_and_score()`:

```python
def classify_and_score(lead: Lead) -> None:
    # ... AI classification ...
    
    # Generate personalized icebreaker
    try:
        lead.ice = generate_icebreaker(lead)
    except Exception as exc:
        log(f"  Icebreaker generation failed: {exc}")
        lead.ice = ""
    
    # ... scoring ...
```

## Google Sheets

The `ice` column is added to the All_Leads sheet after `personalization_note` and before `phone`.

## Testing

Run the tests:

```bash
# Unit tests
pytest tests/test_icebreaker_generator.py

# Quick manual test
python test_icebreaker_quick.py
```

## Troubleshooting

**No icebreakers are being generated**
- Check that `OPENROUTER_API_KEY` is set in `.env`
- Verify the API key is valid at https://openrouter.ai/
- Check logs for "OpenRouter API key not configured"

**Icebreakers are generic or low quality**
- Try adjusting `ICEBREAKER_TONE` to be more specific
- Try a different OpenRouter model (e.g., `openai/gpt-4o` instead of free models)
- Ensure website content is being extracted properly

**API timeouts**
- Free models can be slow; consider using a paid model
- Increase `REQUEST_TIMEOUT_SECONDS` in `.env`

**Too expensive**
- Use a cheaper model like `qwen/qwen3.6-plus:free` (free but slower)
- Reduce `ICEBREAKER_LENGTH` to 1 sentence
- Disable icebreaker generation by removing `OPENROUTER_API_KEY`

## Cost Considerations

Each icebreaker generation makes one API call with:
- Input tokens: ~500-1000 (system prompt + website content)
- Output tokens: ~50-150 (depending on `ICEBREAKER_LENGTH`)

Estimated cost per icebreaker:
- Free models: $0.00
- `openai/gpt-4o-mini`: ~$0.001
- `openai/gpt-4o`: ~$0.01

For 100 leads/day:
- Free: $0.00/day
- `gpt-4o-mini`: ~$0.10/day
- `gpt-4o`: ~$1.00/day
