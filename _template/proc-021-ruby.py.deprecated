import argparse
import os
import glob
import logging
import time
import re
import difflib
import json
import subprocess
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configuration ---
MODEL_NAME = "gemini-3-pro-preview"
MAX_RETRIES = 3
TEMPERATURE = 0.1
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
    # Construct URL based on LOCATION
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
            "temperature": TEMPERATURE
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




def remove_ruby_syntax(text):
    """
    Removes Aozora Bunko ruby format from the text to retrieve the base text.
    Pattern: |Base《Reading》 or Base《Reading》
    """
    text = re.sub(r'[｜|]', '', text)
    text = re.sub(r'《[^》]+》', '', text)
    return text

def validate_integrity(original, generated):
    clean_generated = remove_ruby_syntax(generated)
    clean_original = remove_ruby_syntax(original)
    
    def normalize(t):
        return "".join(t.split())

    # 1. Strict comparison
    if normalize(clean_original) == normalize(clean_generated):
        return True, ""

    # 2. Permissive comparison for parenthesized readings
    # If original has "蹄（ひづめ）" and generated has "|蹄《ひづめ》" -> "蹄" (clean_generated),
    # removing parens from original makes them match.
    def remove_parens(t):
        return re.sub(r'（[^）]+）', '', t)

    if normalize(remove_parens(clean_original)) == normalize(remove_parens(clean_generated)):
        return True, "Parentheses conversion detected"

    diff = difflib.unified_diff(
        clean_original.splitlines(),
        clean_generated.splitlines(),
        fromfile='Original',
        tofile='Generated',
        lineterm=''
    )
    return False, "\n".join(diff)

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
あなたは出版社の校正担当者です。
以下のテキストに、読みやすさを向上させるためのルビ（ふりがな）を振ってください。

## ルール
1. **青空文庫形式**でルビを振ってください。
   形式: `|漢字《かんじ》`
   ※ ルビを振る対象の漢字の直前に `|` (半角パイプ) を入れ、直後に `《よみ》` を入れてください。
   例: `|挨拶《あいさつ》`

2. **絶対遵守事項: 原文の保持**
   - 元のテキストの文字、記号、改行は**絶対に削除・変更・追加しないでください**。
   - 許可される変更は「ルビ記号（`|` と `《...》`）の挿入」のみです。
   - 一文字でも原文と異なれば、あなたの作業は不合格となります。

3. **ルビの基準（厳格化）**
   - **難読漢字、特殊な読み方の語、固有名詞（人名・地名）**にのみルビを振ってください。
   - **常用漢字や、一般的に広く使われている熟語には、絶対にルビを振らないでください。**
     - 振らない例: 挨拶、確信、背後、不意、肥満、紳士、筋肉、時計、新聞、椅子、帽子、説明、到着、意味、理由、非常、単純
   - 中学校までに習う程度の漢字にはルビを振らないでください。
   - **「迷ったら振らない」**を徹底してください。過剰なルビは読書の妨げになります。
4. **重複の禁止（初出のみ）**
   - 同じ単語へのルビは、**その文章内で最初に出てきた1回目のみ**振ってください。
   - 2回目以降に出てくる同じ単語には、ルビを振らないでください。くどいルビは読みやすさを損ないます。
5. **括弧書きの処理**
   - 原文に `漢字（よみ）` という形式がある場合の処理：
     - **一般的な読み仮名**（辞書的な読み）の場合：青空文庫形式のルビ `|漢字《よみ》` に変換してください。（例: `蹄（ひづめ）` → `|蹄《ひづめ》`）
     - **特殊な読み替え（当て字）**や**意味の説明**の場合：変換せず、そのまま**括弧書き**で残してください。（例: `女性（ひと）` → `女性（ひと）` のまま）

## 対象テキスト
```
{original_text}
```

出力は、ルビを振った後のテキストのみを行ってください。前置きやMarkdownのコードブロック記号は不要です。
    """

    for attempt in range(MAX_RETRIES):
        try:
            generated_text = generate_content_vertex_rest(project_id, token, prompt)
            generated_text = generated_text.strip()
            
            if generated_text.startswith("```"):
                generated_text = re.sub(r'^```\w*\n', '', generated_text)
                generated_text = re.sub(r'\n```$', '', generated_text)
            
            is_valid, diff = validate_integrity(original_text, generated_text)
            
            if is_valid:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(generated_text)
                return "SUCCESS"
            else:
                logger.warning(f"Validation failed for {filename} (Attempt {attempt+1}):\n{diff[:500]}...")
                
        except Exception as e:
            logger.error(f"Error processing {filename} (Attempt {attempt+1}): {str(e)}")
            time.sleep(2)
            
    logger.error(f"Failed to generate valid ruby for {filename} after {MAX_RETRIES} attempts. Writing original text.")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(original_text)
    return "FALLBACK"

def main():
    parser = argparse.ArgumentParser(description="Generate Ruby for Markdown files using Vertex AI (REST)")
    parser.add_argument("--input", required=True, help="Input directory")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--log", default="ruby_gen.log", help="Log file path")
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
    
    # Process sequentially or use ThreadPool (careful with token expiry if long running, but okay for short)
    # Token usually lasts 1 hour.
    
    with ThreadPoolExecutor(max_workers=5) as executor:
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