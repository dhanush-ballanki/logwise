from google import genai
import os

client = genai.Client()

def ai_analyze_err(command: str, stderr:str, exit_code: int) -> dict:
    """
        Use AI to analyze error
    """
    if not os.getenv("GEMINI_API_KEY"):
        return {
            'error': 'Gemini API key not set. Set env var GEMINI_API_KEY',
        }
    prompt = f"""
    Analyze this command error:
    Command: {command}
    Exit code: {exit_code}
    Stderr: {stderr}
    
    Provide:
    - A simple human-readable reason for the error.
    - Step-by-step instructions to fix it.
    Keep it concise, under 200 words.
    """

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config={
                "max_output_tokens": 700,
                "temperature": 0.7,
            }
        )

        analysis = response.text.strip()
        parts = analysis.split("Step-by-step instructions to fix it:", 1)

        reason = (
            parts[0]
            .replace("A simple human-readable reason for the error:", "")
            .strip()
        )

        fixes = parts[1].strip() if len(parts) > 1 else "No fixes suggested."

        return {
            "reason": reason,
            "fixes": fixes,
        }
        

    except Exception as e:
        return {'error':f"AI analysis failed: {str(e)}"}