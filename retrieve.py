import os
import xml.etree.ElementTree as ET
from typing import List

import requests


def fetch_latest_cases(num: int = 100) -> bytes:
    base_url = "https://crd.ndl.go.jp/api/refsearch"
    params = {"results_num": str(num), "type": "all", "query": 'anywhere="図書館"'}
    print("送信パラメータ:", params)
    resp = requests.get(base_url, params=params)
    print("リクエスト URL:", resp.url)
    resp.raise_for_status()
    print("レスポンスステータス:", resp.status_code)
    return resp.content


def parse_and_save(xml_data: bytes, output_dir: str = "cases") -> None:
    os.makedirs(output_dir, exist_ok=True)
    root = ET.fromstring(xml_data)
    references: List[ET.Element] = root.findall(".//reference")
    print(f"`<reference>` 要素数: {len(references)}")

    count_saved = 0
    for idx, ref in enumerate(references, start=1):
        question = (ref.findtext("question") or "").strip()
        answer = (ref.findtext("answer") or "").strip()

        if not (question or answer):
            print(f"case_{idx:03} は質問も回答も空。スキップします。")
            continue

        body = f"【質問】\n{question}\n\n【回答】\n{answer}"
        filename = os.path.join(output_dir, f"case_{idx:03}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(body)
        count_saved += 1
        print(f"保存: {filename}")

    print(f"保存済ファイル数: {count_saved}")


def main() -> None:
    xml = fetch_latest_cases(100)
    parse_and_save(xml)


if __name__ == "__main__":
    main()
