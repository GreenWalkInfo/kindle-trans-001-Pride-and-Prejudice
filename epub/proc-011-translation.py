import argparse
import os
import glob
import logging
import time
import subprocess
import requests
import json
from datetime import datetime

# --- Configuration ---
DEFAULT_MODEL = "gemini-3.1-pro-preview"
MAX_RETRIES = 5
INITIAL_WAIT = 5
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

# --- GCP Auth Helpers ---
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

# --- API Interaction ---
def generate_translation(project_id, token, prompt, model=DEFAULT_MODEL, logger=None):
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
            "temperature": 0.1,
            "thinkingConfig": {
                "thinkingLevel": "HIGH"
            }
        }
    }
    
    wait_time = INITIAL_WAIT
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            
            elif response.status_code == 429:
                if logger:
                    logger.warning(f"429 Too Many Requests (Attempt {attempt+1}/{MAX_RETRIES}). Waiting {wait_time}s...")
                time.sleep(wait_time)
                wait_time *= 2
            else:
                raise RuntimeError(f"API Error {response.status_code}: {response.text}")
                
        except Exception as e:
            if logger:
                logger.error(f"Request failed (Attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(wait_time)
            wait_time *= 2
            
    raise RuntimeError(f"Failed after {MAX_RETRIES} attempts due to API limits or errors.")

# --- Context Builder ---
def build_prompt(input_file, reference_files, resources):
    with open(input_file, 'r', encoding='utf-8') as f:
        source_text = f.read()

    combined_prompt = f"""# 『{resources['title']}』翻訳・ルビ・注釈統合プロンプト

このプロンプトは、以下の5つの文書を統合したものです。翻訳時は必ずすべての指示に従ってください。

***

## Part 1: 翻訳システムプロンプト
{resources['system_prompt']}

***

## Part 2: キャラクターデータベース
{resources['character_db']}

***

## Part 3: 翻訳統一方針書
{resources['standardize_rules']}

***

## Part 4: ルビ付与ルール
{resources['ruby_rules']}

***

## Part 5: 注釈付与ルール
{resources['annotation_rules']}

***

## 実行指示

以下の英語Markdownを上記のすべてのルールに従って日本語に翻訳し、**ルビと注釈を付与した最終的なMarkdown**を出力してください。

**重要事項（再確認）**:
- **翻訳品質**: システムプロンプトの文体方針とキャラクターDBの話し方設定を厳守し、現代のキャラ文芸として読みやすくすること。
- **表記統一**: 統一方針書の表記ルールを機械的に適用すること。
- **見出しと画像**: 見出しは「第X章」のように翻訳し、画像参照の `alt text` も日本語にすること。
- **ルビのインライン付与**: 翻訳テキストを出力する際、必ず「青空文庫形式」のルビ（例: `|親文字《ルビ》`）を同時に埋め込むこと。
- **注釈の付与とリスト化**: 注釈が必要な用語にはインラインマーカー（`[^1]`）を挿入し、**出力の最後尾**に必ず脚注リスト（`[^1]: 説明文`）を出力すること。
- 出力形式: **Markdown形式のみ**（あなたの思考プロセスや「承知しました」などの前置き、出力後の解説は一切不要です。純粋なMarkdownテキストのみを出力してください）。

"""

    # 参照ファイルの追加
    for ref_file in reference_files:
        if ref_file and os.path.exists(ref_file) and os.path.basename(ref_file) != os.path.basename(input_file):
            with open(ref_file, 'r', encoding='utf-8') as f:
                combined_prompt += f"""

***

## 参考情報：{os.path.basename(ref_file)} の翻訳（文脈とスタイルの参考）
{f.read()}
"""

    combined_prompt += f"""

***

## 翻訳対象（原文）

{source_text}
"""
    
    return combined_prompt

def main():
    parser = argparse.ArgumentParser(description="Translate Markdown files using Vertex AI with Context and Thinking Level HIGH.")
    parser.add_argument("--input_dir", default="_output/out-002-split-section", help="Input directory")
    parser.add_argument("--output_dir", default="_output/out-011-translated", help="Output directory")
    parser.add_argument("--target", help="Specific filename to translate (e.g., 03_chap03.md)")
    parser.add_argument("--out-filename", help="Override output filename (only valid when --target is used)")
    parser.add_argument("--references", nargs='*', help="List of reference Markdown files (e.g., _output/out-011-translated/01_chap01.md)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name")
    
    args = parser.parse_args()
    
    if args.out_filename and not args.target:
        print("Error: --out-filename can only be used when --target is specified.")
        return

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs("_output/logs", exist_ok=True)
    logger = setup_logging("_output/logs/translation_py.log")

    try:
        project_id = get_gcloud_project()
        token = get_gcloud_token()
    except Exception as e:
        logger.error(f"GCP Authentication failed: {e}")
        return

    # 共通リソースの読み込み
    try:
        resources = {
            'title': "高慢と偏見",
            'system_prompt': open("_output/out-003-system-prompt.md", 'r').read(),
            'character_db': open("_output/out-004-character.md", 'r').read(),
            'standardize_rules': open("_output/out-005-standardize.md", 'r').read(),
            'ruby_rules': open("_output/out-006-ruby.md", 'r').read(),
            'annotation_rules': open("_output/out-007-annotation.md", 'r').read()
        }
    except FileNotFoundError as e:
        logger.error(f"Required resource file not found: {e}")
        return

    # ファイルリストの取得とソート
    files = sorted(glob.glob(os.path.join(args.input_dir, "*.md")))
    
    # ターゲット指定がある場合
    if args.target:
        target_path = os.path.join(args.input_dir, args.target)
        if not os.path.exists(target_path):
            logger.error(f"Target file not found: {target_path}")
            return
        files_to_process = [target_path]
    else:
        files_to_process = files

    all_translated = sorted(glob.glob(os.path.join(args.output_dir, "*.md")))

    for file_path in files_to_process:
        filename = os.path.basename(file_path)
        
        # 出力ファイル名の決定
        out_name = args.out_filename if args.out_filename else filename
        output_path = os.path.join(args.output_dir, out_name)
        
        # 既存ファイルのチェック（ターゲット指定時は上書き）
        if not args.target and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Skipping: {filename} (Already exists)")
            continue

        # 参照ファイルの決定
        reference_files = []
        if args.references is not None:
            # ユーザー指定の参照ファイルを使用
            reference_files = args.references
        else:
            # デフォルト動作：第1章と直前の章を自動特定
            if all_translated:
                reference_files.append(all_translated[0]) # 先頭ファイル
            
            current_idx = next((i for i, f in enumerate(files) if os.path.basename(f) == filename), None)
            if current_idx is not None and current_idx > 0:
                prev_filename = os.path.basename(files[current_idx - 1])
                potential_prev = os.path.join(args.output_dir, prev_filename)
                if os.path.exists(potential_prev) and potential_prev not in reference_files:
                    reference_files.append(potential_prev)

        logger.info(f"Translating: {filename} -> {out_name} (Thinking Level: HIGH)")
        if reference_files:
            logger.info(f"  Using references: {', '.join([os.path.basename(r) for r in reference_files])}")
        
        prompt = build_prompt(file_path, reference_files, resources)
        
        try:
            translated_text = generate_translation(project_id, token, prompt, model=args.model, logger=logger)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(translated_text)
            logger.info(f"Successfully translated: {out_name}")
            
            # 連続処理時、翻訳結果をall_translatedに追加して直前コンテキストとして使えるようにする
            if output_path not in all_translated:
                all_translated.append(output_path)
                all_translated.sort()
                
        except Exception as e:
            logger.error(f"Failed to translate {filename}: {e}")

    logger.info("Translation process finished.")

if __name__ == "__main__":
    main()
