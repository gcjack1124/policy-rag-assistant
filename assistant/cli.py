#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cli.py — 管理辦法小幫手 CLI（D 介面層）

把無狀態 core answer() 包成互動式問答。
安全邊界（★程式碼守、非 LLM）：輸入長度上限、prompt 硬化（在 GEN_SYSTEM）、參考日由程式給。

用法：
  互動：python cli.py
  單次：python cli.py "出差住宿費上限多少？"
  互動指令：:date YYYY-MM-DD 切換參考日（測時間版本）｜:date 切回今天｜:help｜:quit
"""
import sys
from datetime import date

from rag import load_config, load_catalog, answer

MAX_INPUT = 200  # 輸入長度上限（擋洪水/刷 token；在打 API 前先擋）


def ask(question, catalog, cfg, ref_date):
    q = (question or "").strip()
    if not q:
        return None
    if len(q) > MAX_INPUT:
        return f"⚠️ 問題過長（{len(q)} 字，上限 {MAX_INPUT} 字）。請精簡後再問。"
    return answer(q, catalog, cfg, ref_date)["answer_text"]


def main():
    cfg = load_config()
    catalog = load_catalog(cfg)
    ref_date = date.today()

    # 單次模式
    if len(sys.argv) > 1:
        out = ask(" ".join(sys.argv[1:]), catalog, cfg, ref_date)
        if out:
            print(out)
        return

    # 互動模式
    print("=" * 60)
    print(" 管理辦法小幫手（PoC）")
    print(f" 參考日：{ref_date}　|　輸入問題；:help 看指令、:quit 離開")
    print("=" * 60)
    while True:
        try:
            line = input("\n你問> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再見。")
            break
        if not line:
            continue
        if line in (":quit", ":q", "exit"):
            print("再見。")
            break
        if line == ":help":
            print(" :date YYYY-MM-DD 切換參考日（測時間版本）｜:date 切回今天｜:quit 離開")
            continue
        if line.startswith(":date"):
            arg = line[5:].strip()
            if not arg:
                ref_date = date.today()
                print(f" 參考日切回今天：{ref_date}")
            else:
                try:
                    ref_date = date.fromisoformat(arg)
                    print(f" 參考日已設為 {ref_date}")
                except ValueError:
                    print(" 日期格式錯誤，請用 YYYY-MM-DD")
            continue
        out = ask(line, catalog, cfg, ref_date)
        if out:
            print("\n" + out)


if __name__ == "__main__":
    main()
