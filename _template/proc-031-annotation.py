import argparse
import os
import glob
import logging
import time
import re
import json
import subprocess
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configuration ---
MODEL_NAME = "gemini-3-pro-preview"
MAX_RETRIES = 5
TEMPERATURE = 0.5
LOCATION = "global"

# --- Logging Setup ---
def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# --- Helper Functions ---

def get_gcloud_token():
    try:
        result = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get gcloud token: {e.stderr}")

def get_gcloud_project():
    try:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if project:
            return project
        result = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get gcloud project: {e.stderr}")

def generate_content_vertex_rest(project_id, token, prompt, model=MODEL_NAME):
    if LOCATION == "global":
        host = "aiplatform.googleapis.com"
    else:
        host = f"{LOCATION}-aiplatform.googleapis.com"
        
    url = f"https://{host}/v1beta1/projects/{project_id}/locations/{LOCATION}/publishers/google/models/{model}:generateContent"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": TEMPERATURE,
            "responseMimeType": "application/json" 
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        raise RuntimeError(f"API Error {response.status_code}: {response.text}")
        
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        if "promptFeedback" in data and "blockReason" in data["promptFeedback"]:
             raise RuntimeError(f"Blocked: {data['promptFeedback']['blockReason']}")
        raise RuntimeError(f"Unexpected response format: {data}")

def insert_annotations(original_text, annotations, filename=""):
    """
    Inserts annotation markers into the text and appends definitions at the end.
    annotations: list of {"word": "target_word", "description": "text"}
    filename: used to generate unique annotation IDs based on chapter number
    """
    modified_text = original_text
    footer_definitions = []
    
    # Extract chapter ID from filename (e.g., "01_ch1.md" -> "01")
    match = re.search(r'^(\d+)', filename)
    chapter_id = match.group(1) if match else "note"
    
    count = 0
    used_words = set()

    for item in annotations:
        word = item.get("word")
        desc = item.get("description")
        
        if not word or not desc:
            continue
            
        if word in used_words:
            continue

        if word not in modified_text:
            continue

        count += 1
        # ID format: n01_01, n01_02, ... (Prefix 'n' to avoid starting with digit)
        note_id = f"n{chapter_id}_{count:02d}"
        
        # Replace ONLY the first occurrence, avoiding already marked
        escaped_word = re.escape(word)
        # Regex: Match word if NOT followed by [^
        pattern = re.compile(f"({escaped_word})(?!((\[\^)))")
        
        # Perform replacement (only once)
        # Use a lambda for replacement to safely insert backreference and new string
        new_text, n = pattern.subn(lambda m: f"{m.group(1)}[^{note_id}]", modified_text, count=1)
        
        if n > 0:
            modified_text = new_text
            # Footer format: [^ch1_01]: 【word】description
            footer_definitions.append(f"[^{note_id}]: 【{word}】{desc}")
            used_words.add(word)

    if footer_definitions:
        modified_text += "\n\n" + "\n".join(footer_definitions)
        
    return modified_text

def process_single_file(file_path, output_dir, project_id, token, logger):
    filename = os.path.basename(file_path)
    output_path = os.path.join(output_dir, filename)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        original_text = f.read()
    
    if not original_text.strip():
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(original_text)
        return "SKIPPED"

    prompt = f"""
あなたは出版社の編集者です。
以下のテキスト（ルビ付き）を読み、現代の読者が理解しにくい用語（歴史的背景、地理、古い物品、難解語句など）を抽出し、簡潔な解説を作成してください。

## ルール
1. **出力形式**: JSON配列のみを出力してください。
   ```json
   [
     {{"word": "対象単語1", "description": "解説文1"}},
     {{"word": "対象単語2", "description": "解説文2"}}
   ]
   ```
2. **対象の選定**:
   - 物語の理解に役立つもの（1ファイルにつき3〜5個程度）。
   - **必ず本文中にそのままの表記で含まれている単語**を選んでください（ルビ付きの場合はルビを除いた親文字、あるいはルビ付き全体ではなく親文字のみを指定）。
   - 人名や地名、通貨単位、歴史的事象などが優先です。
3. **解説**:
   - 簡潔に（1〜2文）。

## 対象テキスト
```
{original_text}
```
"""

    for attempt in range(MAX_RETRIES):
        try:
            generated_text = generate_content_vertex_rest(project_id, token, prompt)
            
            # Parse JSON
            try:
                annotations = json.loads(generated_text)
                if not isinstance(annotations, list):
                    raise ValueError("Output is not a list")
            except json.JSONDecodeError:
                # Try to clean up if simple markdown wrap
                generated_text = re.sub(r'^```json\s*', '', generated_text)
                generated_text = re.sub(r'\s*```$', '', generated_text)
                annotations = json.loads(generated_text)

            # Insert annotations
            final_text = insert_annotations(original_text, annotations, filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_text)
            return "SUCCESS"

        except Exception as e:
            logger.error(f"Error processing {filename} (Attempt {attempt+1}): {str(e)}")
            time.sleep(10 * (attempt + 1))
            
    logger.error(f"Failed to generate annotations for {filename} after {MAX_RETRIES} attempts. Writing original text.")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(original_text)
    return "FALLBACK"

def main():
    parser = argparse.ArgumentParser(description="Generate Annotations for Markdown files using Vertex AI")
    parser.add_argument("--input", required=True, help="Input directory")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--log", default="annotation_gen.log", help="Log file path")
    parser.add_argument("--pattern", default="*.md", help="Glob pattern for files (default: *.md)")
    
    args = parser.parse_args()
    
    logger = setup_logging(args.log)
    
    try:
        project_id = get_gcloud_project()
        token = get_gcloud_token()
        logger.info(f"Using Project: {project_id}")
    except Exception as e:
        logger.error(f"Failed to set up GCP auth: {e}")
        return

    files = glob.glob(os.path.join(args.input, args.pattern))
    if not files:
        logger.warning(f"No files matching {args.pattern} found in {args.input}")
        return

    os.makedirs(args.output, exist_ok=True)
    
    logger.info(f"Starting processing for {len(files)} files...")
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_to_file = {executor.submit(process_single_file, f, args.output, project_id, token, logger): f for f in files}
        
        count = 0
        total = len(files)
        for future in as_completed(future_to_file):
            count += 1
            file_path = future_to_file[future]
            try:
                result = future.result()
                print(f"[{count}/{total}] {os.path.basename(file_path)}: {result}")
            except Exception as e:
                logger.error(f"Unhandled exception for {file_path}: {e}")

    logger.info("Processing complete.")

if __name__ == "__main__":
    main()